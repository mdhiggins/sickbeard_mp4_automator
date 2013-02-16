#!/usr/bin/python


import os
import os.path

from avcodecs import video_codec_list, audio_codec_list
from formats import format_list

from ffmpeg import FFMpeg, FFMpegError, FFMpegConvertError


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
        self.formats = {}

        for cls in audio_codec_list:
            name = cls.codec_name
            self.audio_codecs[name] = cls

        for cls in video_codec_list:
            name = cls.codec_name
            self.video_codecs[name] = cls

        for cls in format_list:
            name = cls.format_name
            self.formats[name] = cls

    def parse_options(self, opt, twopass=None):
        """
        Parse format/codec options and prepare raw ffmpeg option list.
        """
        format_options = None
        audio_options = []
        video_options = []

        if not isinstance(opt, dict):
            raise ConverterError('Invalid output specification')

        if 'format' not in opt:
            raise ConverterError('Format not specified')

        f = opt['format']
        if f not in self.formats:
            raise ConverterError('Requested unknown format: ' + str(f))

        format_options = self.formats[f]().parse_options(opt)
        if format_options is None:
            raise ConverterError('Unknown container format error')

        if 'audio' not in opt and 'video' not in opt:
            raise ConverterError('Neither audio nor video streams requested')

        if 'audio' not in opt or twopass == 1:
            opt['audio'] = {'codec': None}

        if 'video' not in opt:
            opt['video'] = {'codec': None}

        if 'audio' in opt:
            x = opt['audio']

            if not isinstance(x, dict) or 'codec' not in x:
                raise ConverterError('Invalid audio codec specification')

            c = x['codec']
            if c not in self.audio_codecs:
                raise ConverterError('Requested unknown audio codec ' + str(c))

            audio_options = self.audio_codecs[c]().parse_options(x)
            if audio_options is None:
                raise ConverterError('Unknown audio codec error')

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

        optlist = audio_options + video_options + format_options

        if twopass == 1:
            optlist.extend(['-pass', '1'])
        elif twopass == 2:
            optlist.extend(['-pass', '2'])

        return optlist

    def convert(self, infile, outfile, options, twopass=False, timeout=10):
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

        >>> conv = c.convert('test1.ogg', '/tmp/output.mkv', {
        ...    'format': 'mkv',
        ...    'audio': { 'codec': 'aac' },
        ...    'video': { 'codec': 'h264' }
        ... })

        >>> for timecode in conv:
        ...   pass # can be used to inform the user about the progress
        """

        if not isinstance(options, dict):
            raise ConverterError('Invalid options')

        if not os.path.exists(infile):
            raise ConverterError("Source file doesn't exist: " + infile)

        info = self.ffmpeg.probe(infile)
        if info is None:
            raise ConverterError("Can't get information about source file")

        if not info.video and not info.audio:
            raise ConverterError('Source file has no audio or video streams')

        if info.video and 'video' in options:
            v = options['video']
            v['src_width'] = info.video.video_width
            v['src_height'] = info.video.video_height

        if info.format.duration < 0.01:
            raise ConverterError('Zero-length media')

        if twopass:
            optlist1 = self.parse_options(options, 1)
            for timecode in self.ffmpeg.convert(infile, outfile, optlist,
                    timeout=timeout):
                yield int((50.0 * timecode) / info.format.duration)

            optlist2 = self.parse_options(options, 2)
            for timecode in self.ffmpeg.convert(infile, outfile, optlist2,
                    timeout=timeout):
                yield int(50.0 + (50.0 * timecode) / info.format.duration)
        else:
            optlist = self.parse_options(options, twopass)
            for timecode in self.ffmpeg.convert(infile, outfile, optlist,
                    timeout=timeout):
                yield int((100.0 * timecode) / info.format.duration)

    def probe(self, fname):
        """
        Examine the media file. See the documentation of
        converter.FFMpeg.probe() for details.
        """
        return self.ffmpeg.probe(fname)

    def thumbnail(self, fname, time, outfile, size=None):
        """
        Create a thumbnail of the media file. See the documentation of
        converter.FFMpeg.thumbnail() for details.
        """
        return self.ffmpeg.thumbnail(fname, time, outfile, size)
