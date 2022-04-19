#!/usr/bin/env python3

import os

from converter.avcodecs import video_codec_list, audio_codec_list, subtitle_codec_list, attachment_codec_list, decoder_list, BaseDecoder
from converter.formats import format_list
from converter.ffmpeg import FFMpeg, FFMpegError, FFMpegConvertError


class ConverterError(Exception):
    pass


class Converter(object):
    """
    Converter class, encapsulates formats and codecs.

    >>> c = Converter()
    """

    def __init__(self, ffmpeg_path=None, ffprobe_path=None):
        """
        Initialize a new Converter object.
        """

        self.ffmpeg = FFMpeg(ffmpeg_path=ffmpeg_path,
                             ffprobe_path=ffprobe_path)
        self.video_codecs = {}
        self.audio_codecs = {}
        self.subtitle_codecs = {}
        self.attachment_codecs = {}
        self.formats = {}

        for cls in audio_codec_list:
            name = cls.codec_name
            self.audio_codecs[name] = cls

        for cls in video_codec_list:
            name = cls.codec_name
            self.video_codecs[name] = cls

        for cls in subtitle_codec_list:
            name = cls.codec_name
            self.subtitle_codecs[name] = cls

        for cls in attachment_codec_list:
            name = cls.codec_name
            self.attachment_codecs[name] = cls

        for cls in format_list:
            name = cls.format_name
            self.formats[name] = cls

    @staticmethod
    def ffmpeg_codec_name_to_codec_name(type, ffmpeg_codec_name):
        return next((x.codec_name for x in video_codec_list + audio_codec_list + subtitle_codec_list + attachment_codec_list if x.ffmpeg_codec_name == ffmpeg_codec_name), None)

    @staticmethod
    def codec_name_to_ffprobe_codec_name(codec_name):
        return next((x.ffprobe_codec_name for x in video_codec_list + audio_codec_list + subtitle_codec_list + attachment_codec_list if x.codec_name == codec_name), None)

    @staticmethod
    def codec_name_to_ffmpeg_codec_name(codec_name):
        return next((x.ffmpeg_codec_name for x in video_codec_list + audio_codec_list + subtitle_codec_list + attachment_codec_list if x.codec_name == codec_name), None)

    @staticmethod
    def decoder(decoder):
        return next((x() for x in decoder_list if x.decoder_name == decoder), BaseDecoder())

    @staticmethod
    def encoder(encoder):
        return next((x() for x in video_codec_list + audio_codec_list + subtitle_codec_list + attachment_codec_list if x.codec_name == encoder), None)

    def parse_options(self, opt, twopass=None, strip_metadata=False):
        """
        Parse format/codec options and prepare raw ffmpeg option list.
        """
        format_options = None
        audio_options = []
        video_options = []
        subtitle_options = []
        attachment_options = []
        source_options = []

        if not isinstance(opt, dict):
            raise ConverterError('Invalid output specification')

        try:
            f = opt['format']
            format_options = self.formats[f]().parse_options(opt)
        except:
            format_options = []

        if 'source' not in opt or len(opt['source']) < 1:
            raise ConverterError('No source file provided')

        if 'audio' not in opt and 'video' not in opt and 'subtitle' not in opt:
            raise ConverterError('Neither audio nor video nor subtitle streams requested')

        # Sources
        if 'source' in opt:
            y = opt['source']

            if isinstance(y, str):
                y = [y]

            for x in y:
                if not os.path.exists(x):
                    raise ConverterError('Source file does not exist')
                if 'sub-encoding' in opt:
                    sindex = opt['source'].index(x)
                    if len([x for x in opt.get('subtitle', []) if x.get('source') == sindex]) > 0:
                        source_options.extend(['-sub_charenc', opt['sub-encoding']])
                source_options.extend(['-i', x])

        # Audio
        if 'audio' in opt:
            y = opt['audio']

            # Creates the new nested dictionary to preserve backwards compatability
            if isinstance(y, dict):
                y = [y]

            for x in y:
                if not isinstance(x, dict) or 'codec' not in x:
                    raise ConverterError('Invalid audio codec specification')

                c = x['codec']
                if c not in self.audio_codecs:
                    raise ConverterError('Requested unknown audio codec ' + str(c))

                audio_options.extend(self.audio_codecs[c]().parse_options(x, y.index(x)))
                if audio_options is None:
                    raise ConverterError('Unknown audio codec error')

        # Subtitle
        if 'subtitle' in opt:
            y = opt['subtitle']

            # Creates the new nested dictionary to preserve backwards compatability
            if isinstance(y, dict):
                y = [y]

            for x in y:
                if not isinstance(x, dict) or 'codec' not in x:
                    raise ConverterError('Invalid subtitle codec specification')

                c = x['codec']
                if c not in self.subtitle_codecs:
                    raise ConverterError('Requested unknown subtitle codec ' + str(c))

                subtitle_options.extend(self.subtitle_codecs[c]().parse_options(x, y.index(x)))
                if subtitle_options is None:
                    raise ConverterError('Unknown subtitle codec error')

        # Attachments
        if 'attachment' in opt:
            y = opt['attachment']

            # Creates the new nested dictionary to preserve backwards compatability
            if isinstance(y, dict):
                y = [y]

            for x in y:
                if not isinstance(x, dict) or 'codec' not in x:
                    raise ConverterError('Invalid attachment codec specification')

                if 'filename' not in x:
                    raise ConverterError("Attachment codec requires a filename")

                if 'mimetype' not in x:
                    raise ConverterError("Attachment codec requires a mimetype")

                c = x['codec']
                if c not in self.attachment_codecs:
                    raise ConverterError('Requested unknown attachment codec ' + str(c))

                attachment_options.extend(self.attachment_codecs[c]().parse_options(x, y.index(x)))
                if attachment_options is None:
                    raise ConverterError('Unknown attachment codec error')

        if 'video' in opt:
            x = opt['video']
            if not isinstance(x, dict) or 'codec' not in x:
                raise ConverterError('Invalid video codec specification')

            c = x['codec']
            if c not in self.video_codecs:
                raise ConverterError('Requested unknown video codec ' + str(c))

            video_options = self.video_codecs[c]().parse_options(x)
            if video_options is None:
                raise ConverterError('Unknown video codec error')

        metadata_options = ["-map_metadata", "-1"] if strip_metadata else []

        # aggregate all options
        optlist = source_options + metadata_options + video_options + audio_options + subtitle_options + attachment_options + format_options

        if twopass == 1:
            optlist.extend(['-pass', '1'])
        elif twopass == 2:
            optlist.extend(['-pass', '2'])

        return optlist

    def tag(self, infile, metadata={}, coverpath=None, streaming=0):
        """
        Tag media file (infile) with metadata dictionary and optional cover art
        """
        outfile = infile
        infile = infile + ".tag"
        i = 2
        while os.path.isfile(infile):
            infile = infile + "." + str(i)
            i += 1

        os.rename(outfile, infile)
        opts = ['-i', infile, '-map', '0:v?', '-c:v', 'copy', '-map', '0:a?', '-c:a', 'copy', '-map', '0:s?', '-c:s', 'copy', '-map', '0:t?', '-c:t', 'copy']

        info = self.ffmpeg.probe(infile)
        i = len(info.attachment)

        if coverpath:
            opts.extend(['-attach', coverpath])
            if coverpath.endswith('png'):
                opts.extend(["-metadata:s:t:" + str(i), "mimetype=image/png", "-metadata:s:t:" + str(i), "filename=cover.png"])
            else:
                opts.extend(["-metadata:s:t:" + str(i), "mimetype=image/jpeg", "-metadata:s:t:" + str(i), "filename=cover.jpg"])

        for k in metadata:
            opts.extend(["-metadata", "%s=%s" % (k, metadata[k])])

        if streaming:
            opts.extend(['-reserve_index_space', "%dk" % (streaming)])

        for timecode, debug in self.ffmpeg.convert(outfile, opts):
            yield int((100.0 * timecode) / info.format.duration), debug
        os.remove(infile)

    def convert(self, outfile, options, twopass=False, timeout=10, preopts=None, postopts=None, strip_metadata=False):
        """
        Convert media file (infile) according to specified options, and
        save it to outfile. For two-pass encoding, specify the pass (1 or 2)
        in the twopass parameter.

        Options should be passed as a dictionary. The keys are:
            * format (mandatory, string) - container format; see
              formats.BaseFormat for list of supported formats
            * audio (optional, dict) - audio codec and options; see
              avcodecs.AudioCodec for list of supported options
            * video (optional, dict) - video codec and options; see
              avcodecs.VideoCodec for list of supported options
            * map (optional, int) - can be used to map all content of stream 0

        Multiple audio/video streams are not supported. The output has to
        have at least an audio or a video stream (or both).

        Convert returns a generator that needs to be iterated to drive the
        conversion process. The generator will periodically yield timecode
        of currently processed part of the file (ie. at which second in the
        content is the conversion process currently).

        The optional timeout argument specifies how long should the operation
        be blocked in case ffmpeg gets stuck and doesn't report back. This
        doesn't limit the total conversion time, just the amount of time
        Converter will wait for each update from ffmpeg. As it's usually
        less than a second, the default of 10 is a reasonable default. To
        disable the timeout, set it to None. You may need to do this if
        using Converter in a threading environment, since the way the
        timeout is handled (using signals) has special restriction when
        using threads.

        >>> conv = Converter().convert('test1.ogg', '/tmp/output.mkv', {
        ...    'format': 'mkv',
        ...    'audio': { 'codec': 'aac' },
        ...    'video': { 'codec': 'h264' }
        ... })

        >>> for timecode, debug in conv:
        ...   pass # can be used to inform the user about the progress
        """

        if not isinstance(options, dict):
            raise ConverterError('Invalid options')

        if 'source' not in options:
            raise ConverterError('No source specified')

        infile = options['source'][0]

        info = self.ffmpeg.probe(infile)
        if info is None:
            raise ConverterError("Can't get information about source file")

        if not info.video and not info.audio and not info.subtitle:
            raise ConverterError('Source file has no audio, video, or subtitle streams')

        if info.video and 'video' in options:
            options = options.copy()
            v = options['video'] = options['video'].copy()
            v['src_width'] = info.video.video_width
            v['src_height'] = info.video.video_height

        if not info.format.duration:
            info.format.duration = 0.01

        if info.video and info.format.duration < 0.01:
            raise ConverterError('Zero-length media')

        if twopass:
            optlist1 = self.parse_options(options, 1, strip_metadata=strip_metadata)
            for timecode, debug in self.ffmpeg.convert(outfile,
                                                       optlist1,
                                                       timeout=timeout,
                                                       preopts=preopts,
                                                       postopts=postopts):
                yield int((50.0 * timecode) / info.format.duration), debug

            optlist2 = self.parse_options(options, 2, strip_metadata=strip_metadata)
            for timecode, debug in self.ffmpeg.convert(outfile,
                                                       optlist2,
                                                       timeout=timeout,
                                                       preopts=preopts,
                                                       postopts=postopts):
                yield int(50.0 + (50.0 * timecode) / info.format.duration), debug
        else:
            optlist = self.parse_options(options, twopass, strip_metadata=strip_metadata)
            for timecode, debug in self.ffmpeg.convert(outfile,
                                                       optlist,
                                                       timeout=timeout,
                                                       preopts=preopts,
                                                       postopts=postopts):
                yield int((100.0 * timecode) / info.format.duration), debug

    def probe(self, fname, posters_as_video=True):
        """
        Examine the media file. See the documentation of
        converter.FFMpeg.probe() for details.

        :param posters_as_video: Take poster images (mainly for audio files) as
            A video stream, defaults to True
        """
        return self.ffmpeg.probe(fname, posters_as_video)

    def framedata(self, fname):
        """
        Examine the framedata of file. See the documentation of
        converter.FFMpeg.framedata() for details.

        """
        try:
            return self.ffmpeg.framedata(fname)
        except FFMpegError:
            return None

    def thumbnail(self, fname, time, outfile, size=None, quality=FFMpeg.DEFAULT_JPEG_QUALITY):
        """
        Create a thumbnail of the media file. See the documentation of
        converter.FFMpeg.thumbnail() for details.
        """
        return self.ffmpeg.thumbnail(fname, time, outfile, size, quality)

    def thumbnails(self, fname, option_list):
        """
        Create one or more thumbnail of the media file. See the documentation
        of converter.FFMpeg.thumbnails() for details.
        """
        return self.ffmpeg.thumbnails(fname, option_list)
