#!/usr/bin/env python


class BaseFormat(object):
    """
    Base format class.

    Supported formats are: ogg, avi, mkv, webm, flv, mov, mp4, mpeg
    """

    format_name = None
    ffmpeg_format_name = None

    def parse_options(self, opt):
        if 'format' not in opt or opt.get('format') != self.format_name:
            raise ValueError('invalid Format format')
        return ['-f', self.ffmpeg_format_name]


class OggFormat(BaseFormat):
    """
    Ogg container format, mostly used with Vorbis and Theora.
    """
    format_name = 'ogg'
    ffmpeg_format_name = 'ogg'


class AviFormat(BaseFormat):
    """
    Avi container format, often used vith DivX video.
    """
    format_name = 'avi'
    ffmpeg_format_name = 'avi'


class MkvFormat(BaseFormat):
    """
    Matroska format, often used with H.264 video.
    """
    format_name = 'mkv'
    ffmpeg_format_name = 'matroska'


class WebmFormat(BaseFormat):
    """
    WebM is Google's variant of Matroska containing only
    VP8 for video and Vorbis for audio content.
    """
    format_name = 'webm'
    ffmpeg_format_name = 'webm'


class FlvFormat(BaseFormat):
    """
    Flash Video container format.
    """
    format_name = 'flv'
    ffmpeg_format_name = 'flv'


class MovFormat(BaseFormat):
    """
    Mov container format, used mostly with H.264 video
    content, often for mobile platforms.
    """
    format_name = 'mov'
    ffmpeg_format_name = 'mov'


class Mp4Format(BaseFormat):
    """
    Mp4 container format, the default Format for H.264
    video content.
    """
    format_name = 'mp4'
    ffmpeg_format_name = 'mp4'


class MpegFormat(BaseFormat):
    """
    MPEG(TS) container, used mainly for MPEG 1/2 video codecs.
    """
    format_name = 'mpg'
    ffmpeg_format_name = 'mpegts'


class Mp3Format(BaseFormat):
    """
    Mp3 container, used audio-only mp3 files
    """
    format_name = 'mp3'
    ffmpeg_format_name = 'mp3'


class SrtFormat(BaseFormat):
    """
    SRT subtitle format
    """
    format_name = 'srt'
    ffmpeg_format_name = 'srt'


class WebVTTFormat(BaseFormat):
    """
    VTT subtitle format
    """
    format_name = 'webvtt'
    ffmpeg_format_name = 'webvtt'

class SsaFormat(BaseFormat):
    """
    SSA subtitle format
    """
    format_name = 'ass'
    ffmpeg_format_name = 'ass'

format_list = [
    OggFormat, AviFormat, MkvFormat, WebmFormat, FlvFormat,
    MovFormat, Mp4Format, MpegFormat, Mp3Format, SrtFormat,
    WebVTTFormat, SsaFormat
]
