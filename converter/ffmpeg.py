#!/usr/bin/env python3

from multiprocessing.sharedctypes import Value
import os.path
import os
import re
import signal
from subprocess import Popen, PIPE
import logging
import locale
import json
from converter.avcodecs import BaseCodec, video_codec_list


console_encoding = locale.getdefaultlocale()[1] or 'UTF-8'

STRICT = {
    "very": 2,
    "strict": 1,
    "normal": 0,
    "unofficial": -1,
    "experimental": -2
}


class FFMpegError(Exception):
    pass


class FFMpegConvertError(Exception):
    def __init__(self, message, cmd, output, details=None, pid=0):
        """
        @param    message: Error message.
        @type     message: C{str}

        @param    cmd: Full command string used to spawn ffmpeg.
        @type     cmd: C{str}

        @param    output: Full stdout output from the ffmpeg command.
        @type     output: C{str}

        @param    details: Optional error details.
        @type     details: C{str}
        """
        super(FFMpegConvertError, self).__init__(message)

        self.cmd = cmd
        self.output = output
        self.details = details
        self.pid = pid

    def __repr__(self):
        error = self.details if self.details else self.message
        return ('<FFMpegConvertError error="%s", pid=%s, cmd="%s">' %
                (error, self.pid, self.cmd))

    def __str__(self):
        return self.__repr__()


class MediaFormatInfo(object):
    """
    Describes the media container format. The attributes are:
      * format - format (short) name (eg. "ogg")
      * fullname - format full (descriptive) name
      * bitrate - total bitrate (bps)
      * duration - media duration in seconds
      * filesize - file size
    """

    def __init__(self):
        self.format = None
        self.fullname = None
        self.bitrate = None
        self.duration = None
        self.filesize = None
        self.metadata = {}

    def parse_ffprobe(self, key, val):
        """
        Parse raw ffprobe output (key=value).
        """
        if key == 'format_name':
            self.format = val
        elif key == 'format_long_name':
            self.fullname = val
        elif key == 'bit_rate':
            self.bitrate = MediaStreamInfo.parse_float(val, None)
        elif key == 'duration':
            self.duration = MediaStreamInfo.parse_float(val, None)
        elif key == 'size':
            self.size = MediaStreamInfo.parse_float(val, None)

        if key.startswith('TAG:'):
            key = key.split('TAG:')[1].lower()
            value = val.lower().strip()
            self.metadata[key] = value

    def __repr__(self):
        if self.duration is None:
            return 'MediaFormatInfo(format=%s)' % self.format
        return 'MediaFormatInfo(format=%s, duration=%.2f)' % (self.format,
                                                              self.duration)


class MediaStreamInfo(object):
    """
    Describes one stream inside a media file. The general
    attributes are:
      * index - stream index inside the container (0-based)
      * type - stream type, either 'audio' or 'video'
      * codec - codec (short) name (e.g "vorbis", "theora")
      * codec_desc - codec full (descriptive) name
      * duration - stream duration in seconds
      * map - stream index for ffmpeg mapping
      * metadata - optional metadata associated with a video or audio stream
      * bitrate - stream bitrate in bytes/second
      * attached_pic - (0, 1 or None) is stream a poster image? (e.g. in mp3)
      * fps - average frames per second
    Video-specific attributes are:
      * video_width - width of video in pixels
      * video_height - height of video in pixels
    Audio-specific attributes are:
      * audio_channels - the number of channels in the stream
      * audio_samplerate - sample rate (Hz)
    """

    def __init__(self):
        self.index = None
        self.type = None
        self.codec = None
        self.codec_desc = None
        self.duration = None
        self.bitrate = None
        self.video_width = None
        self.video_height = None
        self.fps = None
        self.video_level = None
        self.pix_fmt = None
        self.profile = None
        self.audio_channels = None
        self.audio_samplerate = None
        self.attached_pic = None
        self.field_order = None
        self.metadata = {}
        self.disposition = {}
        self.color = {}
        self.framedata = {}

    @property
    def json(self):
        language = self.metadata.get("language", "und")
        out = {
            'index': self.index,
            'codec': self.codec
        }

        if self.bitrate:
            out['bitrate'] = self.bitrate

        if self.type == 'audio':
            out['channels'] = self.audio_channels
            out['samplerate'] = self.audio_samplerate
            out['language'] = language
            out['disposition'] = self.dispostr
        elif self.type == 'video':
            out['pix_fmt'] = self.pix_fmt
            out['profile'] = self.profile
            out['fps'] = self.fps
            out['framedata'] = self.framedata
            if self.video_width and self.video_height:
                out['dimensions'] = "%dx%d" % (self.video_width, self.video_height)
            if self.video_level:
                out['level'] = self.video_level
            out['field_order'] = self.field_order
        elif self.type == 'subtitle':
            out['disposition'] = self.dispostr
            out['language'] = language
        elif self.type == 'attachment':
            out['filename'] = self.metadata.get('filename')
            out['mimetype'] = self.metadata.get('mimetype')
        return out

    @property
    def dispostr(self):
        disposition = ''
        for k in self.disposition:
            if k in BaseCodec.DISPOSITIONS:
                if self.disposition[k]:
                    disposition += "+" + k
                else:
                    disposition += "-" + k
        return disposition

    @staticmethod
    def parse_float(val, default=0.0):
        try:
            return float(val)
        except:
            return default

    @staticmethod
    def parse_int(val, default=0):
        try:
            return int(val)
        except:
            return default

    @staticmethod
    def parse_bool(val, default=False):
        try:
            return bool(val)
        except:
            return default

    def parse_ffprobe(self, key, val):
        """
        Parse raw ffprobe output (key=value).
        """

        if key == 'index':
            self.index = self.parse_int(val)
        elif key == 'codec_type':
            self.type = val
        elif key == 'codec_name':
            self.codec = val.lower()
        elif key == 'codec_long_name':
            self.codec_desc = val
        elif key == 'duration':
            self.duration = self.parse_float(val)
        elif key == 'bit_rate':
            self.bitrate = self.parse_int(val, None)
        elif key == 'width':
            self.video_width = self.parse_int(val)
        elif key == 'height':
            self.video_height = self.parse_int(val)
        elif key == 'channels':
            self.audio_channels = self.parse_int(val)
        elif key == 'sample_rate':
            self.audio_samplerate = self.parse_int(val)
        elif key == 'DISPOSITION:attached_pic':
            self.attached_pic = self.parse_int(val)
        elif key == 'profile':
            self.profile = val.lower().replace(" ", "")
        elif key == 'DISPOSITION:forced':
            self.forced = self.parse_bool(self.parse_int(val))
        elif key == 'DISPOSITION:default':
            self.default = self.parse_bool(self.parse_int(val))
        elif key.lower().startswith('tag:bps'):
            self.bitrate = self.bitrate or self.parse_int(val, None)

        if self.bitrate and self.bitrate < 1000:
            self.bitrate = None

        if key.startswith('TAG:'):
            key = key.split('TAG:')[1].lower()
            value = val.lower().strip()
            self.metadata[key] = value

        if key.startswith('DISPOSITION:'):
            key = key.split('DISPOSITION:')[1].lower()
            value = val.lower().strip()
            self.disposition[key] = self.parse_bool(self.parse_int(value))

        if self.type == 'audio':
            if key == 'avg_frame_rate':
                if '/' in val:
                    n, d = val.split('/')
                    n = self.parse_float(n)
                    d = self.parse_float(d)
                    if n > 0.0 and d > 0.0:
                        self.fps = float(n) / float(d)
                elif '.' in val:
                    self.fps = self.parse_float(val)

        if self.type == 'video':
            if key == 'r_frame_rate':
                if '/' in val:
                    n, d = val.split('/')
                    n = self.parse_float(n)
                    d = self.parse_float(d)
                    if n > 0.0 and d > 0.0:
                        self.fps = float(n) / float(d)
                elif '.' in val:
                    self.fps = self.parse_float(val)
            elif key == 'level':
                self.video_level = self.parse_float(val)
                try:
                    codec_class = next(x for x in video_codec_list if x.ffprobe_codec_name == self.codec)
                    self.video_level = codec_class.codec_specific_level_conversion(self.video_level)
                except:
                    pass
            elif key == 'pix_fmt':
                self.pix_fmt = val.lower()
            elif key == "field_order":
                self.field_order = val.lower()
            elif key == "color_range":
                self.color['range'] = val.lower()
            elif key == "color_space":
                self.color['space'] = val.lower()
            elif key == "color_transfer":
                self.color['transfer'] = val.lower()
            elif key == "color_primaries":
                self.color['primaries'] = val.lower()

    def __repr__(self):
        d = ''
        metadata_str = ['%s=%s' % (key, value) for key, value
                        in self.metadata.items()]
        metadata_str = ', '.join(metadata_str)

        if self.type == 'audio':
            d = 'type=%s, codec=%s, channels=%d, rate=%.0f' % (self.type, self.codec, self.audio_channels, self.audio_samplerate)
        elif self.type == 'video':
            d = 'type=%s, codec=%s, width=%d, height=%d, fps=%.1f' % (
                self.type, self.codec, self.video_width, self.video_height,
                self.fps)
        elif self.type == 'subtitle':
            d = 'type=%s, codec=%s' % (self.type, self.codec)
        if self.bitrate is not None:
            d += ', bitrate=%d' % self.bitrate

        if self.metadata:
            value = 'MediaStreamInfo(%s, %s)' % (d, metadata_str)
        else:
            value = 'MediaStreamInfo(%s)' % d

        return value


class MediaInfo(object):
    """
    Information about media object, as parsed by ffprobe.
    The attributes are:
      * format - a MediaFormatInfo object
      * streams - a list of MediaStreamInfo objects
      * path - path to file
    """

    def __init__(self, posters_as_video=True):
        """
        :param posters_as_video: Take poster images (mainly for audio files) as
            A video stream, defaults to True
        """
        self.format = MediaFormatInfo()
        self.posters_as_video = posters_as_video
        self.streams = []
        self.framedata = []
        self.path = None

    @property
    def json(self):
        return {'format': self.format.format,
                'format-fullname': self.format.fullname,
                'video': self.video.json,
                'audio': [x.json for x in self.audio],
                'subtitle': [x.json for x in self.subtitle],
                'attachment': [x.json for x in self.attachment]}

    def parse_ffprobe(self, raw):
        """
        Parse raw ffprobe output.
        """
        in_format = False
        current_stream = None

        for line in raw.split('\n'):
            line = line.strip()
            if line == '':
                continue
            elif line == '[STREAM]':
                current_stream = MediaStreamInfo()
            elif line == '[/STREAM]':
                if current_stream.type:
                    self.streams.append(current_stream)
                current_stream = None
            elif line == '[FORMAT]':
                in_format = True
            elif line == '[/FORMAT]':
                in_format = False
            elif '=' in line:
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip()
                if current_stream:
                    current_stream.parse_ffprobe(k, v)
                elif in_format:
                    self.format.parse_ffprobe(k, v)

    def __repr__(self):
        return 'MediaInfo(format=%s, streams=%s)' % (repr(self.format),
                                                     repr(self.streams))

    @property
    def video(self):
        """
        First video stream, or None if there are no video streams.
        """
        for s in self.streams:
            if s.type == 'video' and (self.posters_as_video or not s.attached_pic):
                return s
        return None

    @property
    def posters(self):
        return [s for s in self.streams if s.attached_pic]

    @property
    def audio(self):
        """
        All audio streams
        """
        result = []
        for s in self.streams:
            if s.type == 'audio':
                result.append(s)
        return result

    @property
    def subtitle(self):
        """
        All subtitle streams
        """
        result = []
        for s in self.streams:
            if s.type == 'subtitle':
                result.append(s)
        return result

    @property
    def attachment(self):
        """
        All attachment streams
        """
        result = []
        for s in self.streams:
            if s.type == 'attachment':
                result.append(s)
        return result


class FFMpeg(object):
    """
    FFMPeg wrapper object, takes care of calling the ffmpeg binaries,
    passing options and parsing the output.

    >>> f = FFMpeg()
    """
    DEFAULT_JPEG_QUALITY = 4
    CODECS_LINE_RE = re.compile(
        r'^ ([A-Z.]{6}) ([^ \=]+) +(.+)$', re.M)
    CODECS_DECODERS_RE = re.compile(
        r' \(decoders: ([^)]+) \)')
    CODECS_ENCODERS_RE = re.compile(
        r' \(encoders: ([^)]+) \)')
    DECODER_SYNONYMS = {
        'mpeg1video': 'mpeg1',
        'mpeg2video': 'mpeg2'}

    def __init__(self, ffmpeg_path=None, ffprobe_path=None):
        """
        Initialize a new FFMpeg wrapper object. Optional parameters specify
        the paths to ffmpeg and ffprobe utilities.
        """

        def which(name):
            path = os.environ.get('PATH', os.defpath)
            for d in path.split(os.pathsep):
                fpath = os.path.join(d, name)
                if os.path.exists(fpath) and os.access(fpath, os.X_OK):
                    return fpath
            return None

        if ffmpeg_path is None:
            ffmpeg_path = 'ffmpeg'

        if ffprobe_path is None:
            ffprobe_path = 'ffprobe'

        if '/' not in ffmpeg_path:
            ffmpeg_path = which(ffmpeg_path) or ffmpeg_path
        if '/' not in ffprobe_path:
            ffprobe_path = which(ffprobe_path) or ffprobe_path

        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

        if not os.path.exists(self.ffmpeg_path):
            raise FFMpegError("ffmpeg binary not found: " + self.ffmpeg_path)

        if not os.path.exists(self.ffprobe_path):
            raise FFMpegError("ffprobe binary not found: " + self.ffprobe_path)

    @property
    def codecs(self):
        codecs = self._get_stdout([self.ffprobe_path, '-hide_banner', '-codecs'])
        codecs = {
            line_match.group(2): (line_match.group(1), line_match.group(3))
            for line_match in self.CODECS_LINE_RE.finditer(codecs)}

        for codec, coders in codecs.items():
            decoders_match = self.CODECS_DECODERS_RE.search(coders[1])
            encoders_match = self.CODECS_ENCODERS_RE.search(coders[1])
            self_encoder = [codec] if coders[0][1] == "E" else []
            self_decoder = [codec] if coders[0][0] == "D" else []
            codecs[codec] = dict(decoders=decoders_match and decoders_match.group(1).split() or self_decoder, encoders=encoders_match and encoders_match.group(1).split() or self_encoder)
        return codecs

    @property
    def hwaccels(self):
        return [hwaccel.strip() for hwaccel in self._get_stdout([self.ffmpeg_path, '-hide_banner', '-hwaccels']).split('\n')[1:] if hwaccel.strip()]

    @property
    def encoders(self):
        encoders = self._get_stdout([self.ffmpeg_path, '-hide_banner', '-encoders'])
        return [line_match.group(2) for line_match in self.CODECS_LINE_RE.finditer(encoders)]

    @property
    def decoders(self):
        decoders = self._get_stdout([self.ffmpeg_path, '-hide_banner', '-decoders'])
        return [line_match.group(2) for line_match in self.CODECS_LINE_RE.finditer(decoders)]

    @property
    def pix_fmts(self):
        formats = {}
        formatlines = [f.strip() for f in self._get_stdout([self.ffmpeg_path, '-hide_banner', '-pix_fmts']).split('\n')[8:] if f.strip()]
        for f in formatlines:
            frmt = [x for x in f.split(" ") if x]
            if len(frmt) == 5:
                bitdepth = max([int(b) for b in frmt[4].split("-")])
                formats[str(frmt[1])] = bitdepth
        return formats

    def hwaccel_decoder(self, video_codec, hwaccel):
        source_codec = self.DECODER_SYNONYMS.get(video_codec, video_codec)
        return '{0}_{1}'.format(source_codec, hwaccel)

    def encoder_formats(self, encoder):
        prefix = "Supported pixel formats:"
        formatline = next((line.strip() for line in self._get_stdout([self.ffmpeg_path, '-hide_banner', '-h', 'encoder=%s' % encoder]).split('\n')[1:] if line and line.strip().startswith(prefix)), "")
        formats = formatline.split(":")
        return formats[1].strip().split(" ") if formats and len(formats) > 0 else []

    def decoder_formats(self, decoder):
        prefix = "Supported pixel formats:"
        formatline = next((line.strip() for line in self._get_stdout([self.ffmpeg_path, '-hide_banner', '-h', 'decoder=%s' % decoder]).split('\n')[1:] if line and line.strip().startswith(prefix)), "")
        formats = formatline.split(":")
        return formats[1].strip().split(" ") if formats and len(formats) > 0 else []

    @staticmethod
    def _spawn(cmds):
        clean_cmds = []
        try:
            for cmd in cmds:
                clean_cmds.append(str(cmd))
            cmds = clean_cmds
        except KeyboardInterrupt:
            raise
        except:
            raise FFMpegError("There was an error making all command line parameters a string")
        return Popen(cmds, shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE,
                     close_fds=(os.name != 'nt'), startupinfo=None)

    def _get_stdout(self, cmds):
        """
        Return the decoded stdout output for the command.
        """
        p = self._spawn(cmds)
        stdout_data, stderr = p.communicate()
        return stdout_data.decode(console_encoding, errors='ignore')

    def framedata(self, fname):
        try:
            stdout_data = self._get_stdout([
                self.ffprobe_path, '-hide_banner', '-loglevel', 'warning',
                '-select_streams', 'v:0', '-print_format', 'json',
                '-show_frames', '-read_intervals', '%+#1',
                '-show_entries', 'frame=color_space,color_primaries,color_transfer,side_data_list,pix_fmt',
                '-probesize', '50M', '-analyzeduration', '100M',
                '-i', fname])
            return json.loads(stdout_data)['frames'][0]
        except KeyboardInterrupt:
            raise
        except:
            raise FFMpegError("Unable to obtain FFMPEG framedata")

    def probe(self, fname, posters_as_video=True):
        """
        Examine the media file and determine its format and media streams.
        Returns the MediaInfo object, or None if the specified file is
        not a valid media file.

        >>> info = FFMpeg().probe('test1.ogg')
        >>> info.format
        'ogg'
        >>> info.duration
        33.00
        >>> info.video.codec
        'theora'
        >>> info.video.width
        720
        >>> info.video.height
        400
        >>> info.audio.codec
        'vorbis'
        >>> info.audio.channels
        2
        :param posters_as_video: Take poster images (mainly for audio files) as
            A video stream, defaults to True
        """

        if not os.path.exists(fname):
            return None

        info = MediaInfo(posters_as_video)
        info.path = fname

        stdout_data = self._get_stdout([
            self.ffprobe_path, '-show_format', '-show_streams', '-show_entries', 'stream_tags:format_tags', fname])
        info.parse_ffprobe(stdout_data)

        if not info.format.format and len(info.streams) == 0:
            return None

        try:
            info.video.framedata = self.framedata(fname)
        except KeyboardInterrupt:
            raise
        except:
            pass

        return info

    def generateCommands(self, outfile, opts, preopts=None, postopts=None):
        print()
        cmds = [self.ffmpeg_path]
        if preopts:
            cmds.extend(preopts)

        cmds.extend(opts)
        if postopts:
            cmds.extend(postopts)

        self.minstrict(cmds)

        if outfile:
            cmds.extend(['-y', outfile])
        else:
            cmds.extend(['-f', 'null', '-'])
        return cmds

    def minstrict(self, cmds):
        """
        Ensure that only one -strict parameter ends up in the final
        command and use the least strict option specified
        """
        if cmds.count("-strict") > 1:
            strictmin = max(STRICT.values())
            indices = []
            for index, cmd in enumerate(cmds):
                if cmd == '-strict':
                    svalue = cmds[index + 1]
                    try:
                        svalue = int(svalue)
                    except:
                        svalue = STRICT.get(svalue, strictmin)
                    strictmin = min((svalue, strictmin))
                    indices.extend([index, index + 1])
            indices = sorted(indices, reverse=True)
            for idx in indices:
                if idx < len(cmds):
                    cmds.pop(idx)
            cmds.extend(['-strict', str(strictmin)])

    def convert(self, outfile, opts, timeout=10, preopts=None, postopts=None):
        """
        Convert the source media (infile) according to specified options
        (a list of ffmpeg switches as strings) and save it to outfile.

        Convert returns a generator that needs to be iterated to drive the
        conversion process. The generator will periodically yield timecode
        of currently processed part of the file (ie. at which second in the
        content is the conversion process currently).

        The optional timeout argument specifies how long should the operation
        be blocked in case ffmpeg gets stuck and doesn't report back. See
        the documentation in Converter.convert() for more details about this
        option.

        >>> conv = FFMpeg().convert('test.ogg', '/tmp/output.mp3',
        ...    ['-acodec libmp3lame', '-vn'])
        >>> for timecode, debug in conv:
        ...    pass # can be used to inform the user about conversion progress

        """
        if os.name == 'nt':
            timeout = 0
            if outfile and len(outfile) > 260:
                outfile = '\\\\?\\' + outfile

        infile = opts[opts.index("-i") + 1]

        if not os.path.exists(infile):
            raise FFMpegError("Input file doesn't exist: " + infile)

        cmds = self.generateCommands(outfile, opts, preopts, postopts)

        yield 0, cmds

        if timeout:
            def on_sigalrm(*_):
                signal.signal(signal.SIGALRM, signal.SIG_DFL)
                raise Exception('timed out while waiting for ffmpeg')

            signal.signal(signal.SIGALRM, on_sigalrm)

        try:
            p = self._spawn(cmds)
        except OSError:
            raise FFMpegError('Error while calling ffmpeg binary')

        yielded = False
        buf = ''
        total_output = ''
        pat = re.compile(r'time=([0-9.:]+) ')
        while True:
            if timeout:
                signal.alarm(timeout)

            ret = p.stderr.read(10)

            if timeout:
                signal.alarm(0)

            if not ret:
                # For small or very fast jobs, ffmpeg may never output a '\r'.  When EOF is reached, yield if we haven't yet.
                if not yielded:
                    yielded = True
                    yield 10, ""
                break

            try:
                ret = ret.decode(console_encoding)
            except UnicodeDecodeError:
                try:
                    ret = ret.decode(console_encoding, errors="ignore")
                except:
                    pass

            total_output += ret
            buf += ret
            if '\r' in buf:
                line, buf = buf.split('\r', 1)

                tmp = pat.findall(line)
                if len(tmp) == 1:
                    timespec = tmp[0]
                    if ':' in timespec:
                        timecode = 0
                        for part in timespec.split(':'):
                            timecode = 60 * timecode + float(part)
                    else:
                        timecode = float(tmp[0])
                    yielded = True
                    debug = line.strip()
                    debug = debug if debug.startswith("frame") else ""
                    yield timecode, debug

        if timeout:
            signal.signal(signal.SIGALRM, signal.SIG_DFL)

        p.communicate()  # wait for process to exit

        if total_output == '':
            raise FFMpegError('Error while calling ffmpeg binary')

        cmd = ' '.join(cmds)
        if '\n' in total_output:
            line = total_output.split('\n')[-2]

            if line.startswith('Received signal'):
                # Received signal 15: terminating.
                raise FFMpegConvertError(line.split(':')[0], cmd, total_output, pid=p.pid)
            if line.startswith(infile + ': '):
                err = line[len(infile) + 2:]
                raise FFMpegConvertError('Encoding error', cmd, total_output,
                                         err, pid=p.pid)
            if line.startswith('Error while '):
                raise FFMpegConvertError('Encoding error', cmd, total_output,
                                         line, pid=p.pid)
            if not yielded:
                raise FFMpegConvertError('Unknown ffmpeg error', cmd,
                                         total_output, line, pid=p.pid)
        if p.returncode != 0:
            raise FFMpegConvertError('Exited with code %d' % p.returncode, cmd,
                                     total_output, pid=p.pid)

    def thumbnail(self, fname, time, outfile, size=None, quality=DEFAULT_JPEG_QUALITY):
        """
        Create a thumbnal of media file, and store it to outfile
        @param time: time point (in seconds) (float or int)
        @param size: Size, if specified, is WxH of the desired thumbnail.
            If not specified, the video resolution is used.
        @param quality: quality of jpeg file in range 2(best)-31(worst)
            recommended range: 2-6

        >>> FFMpeg().thumbnail('test1.ogg', 5, '/tmp/shot.png', '320x240')
        """
        return self.thumbnails(fname, [(time, outfile, size, quality)])

    def thumbnails(self, fname, option_list):
        """
        Create one or more thumbnails of video.
        @param option_list: a list of tuples like:
            (time, outfile, size=None, quality=DEFAULT_JPEG_QUALITY)
            see documentation of `converter.FFMpeg.thumbnail()` for details.

        >>> FFMpeg().thumbnails('test1.ogg', [(5, '/tmp/shot.png', '320x240'),
        >>>                                   (10, '/tmp/shot2.png', None, 5)])
        """
        if not os.path.exists(fname):
            raise IOError('No such file: ' + fname)

        cmds = [self.ffmpeg_path, '-i', fname, '-y', '-an']
        for thumb in option_list:
            if len(thumb) > 2 and thumb[2]:
                cmds.extend(['-s', str(thumb[2])])

            cmds.extend([
                '-f', 'image2', '-vframes', '1',
                '-ss', str(thumb[0]), thumb[1],
                '-q:v', str(FFMpeg.DEFAULT_JPEG_QUALITY if len(thumb) < 4 else str(thumb[3])),
            ])

        p = self._spawn(cmds)
        _, stderr_data = p.communicate()
        if stderr_data == '':
            raise FFMpegError('Error while calling ffmpeg binary')
        stderr_data.decode(console_encoding)
        if any(not os.path.exists(option[1]) for option in option_list):
            raise FFMpegError('Error creating thumbnail: %s' % stderr_data)
