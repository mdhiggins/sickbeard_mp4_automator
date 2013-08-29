#!/usr/bin/env python


class BaseCodec(object):
    """
    Base audio/video codec class.
    """

    encoder_options = {}
    codec_name = None
    ffmpeg_codec_name = None

    def parse_options(self, opt):
        if 'codec' not in opt or opt['codec'] != self.codec_name:
            raise ValueError('invalid codec name')
        return None

    def _codec_specific_parse_options(self, safe):
        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe):
        return []

    def safe_options(self, opts):
        safe = {}

        # Only copy options that are expected and of correct type
        # (and do typecasting on them)
        for k, v in opts.items():
            if k in self.encoder_options:
                typ = self.encoder_options[k]
                try:
                    safe[k] = typ(v)
                except:
                    pass

        return safe


class AudioCodec(BaseCodec):
    """
    Base audio codec class handles general audio options. Possible
    parameters are:
      * codec (string) - audio codec name
      * channels (integer) - number of audio channels
      * bitrate (integer) - stream bitrate
      * samplerate (integer) - sample rate (frequency)
      * language (str) - language of audio stream (3 char code)
      * map (int) - stream index

    Supported audio codecs are: null (no audio), copy (copy from
    original), vorbis, aac, mp3, mp2
    """

    encoder_options = {
        'codec': str,
        'language': str,
        'channels': int,
        'bitrate': int,
        'samplerate': int,
        'map': int
    }

    def parse_options(self, opt, stream):
        super(AudioCodec, self).parse_options(opt)
        stream = str(stream)
        safe = self.safe_options(opt)

        if 'channels' in safe:
            c = safe['channels']
            if c < 1 or c > 12:
                del safe['channels']

        if 'bitrate' in safe:
            br = safe['bitrate']
            if br < 8 or br > 1536:
                del safe['bitrate']

        if 'samplerate' in safe:
            f = safe['samplerate']
            if f < 1000 or f > 50000:
                del safe['samplerate']

        if 'language' in safe:
            l = safe['language']
            if len(l) > 3:
                del safe['language']

        safe = self._codec_specific_parse_options(safe)

        optlist = ['-c:a:' + stream, self.ffmpeg_codec_name]
        if 'map' in safe:
            optlist.extend(['-map', '0:' + str(safe['map'])])
        if 'channels' in safe:
            optlist.extend(['-ac:a:' + stream, str(safe['channels'])])
        if 'bitrate' in safe:
            optlist.extend(['-b:a:' + stream, str(safe['bitrate']) + 'k'])
        if 'samplerate' in safe:
            optlist.extend(['-r:a:' + stream, str(safe['samplerate'])])
        if 'language' in safe:
                lang = str(safe['language'])
        else:
            lang = 'und'
        optlist.extend(['-metadata:s:a:' + stream, "language=" + lang])

        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))
        return optlist


class SubtitleCodec(BaseCodec):
    """
    Base subtitle codec class handles general subtitle options. Possible
    parameters are:
      * codec (string) - subtitle codec name (mov_text only one supported currently)
      * language (string) - language of audio stream (3 char code)
      * forced (int) - force subtitles (1 true, 0 false)
      * default (int) - default subtitles (1 true, 0 false)

    Supported subtitle codecs are: null (no subtitle), mov_text
    """

    encoder_options = {
        'codec': str,
        'language': str,
        'forced': int,
        'default': int,
        'map': int,
        'source': int,
        'path' : str
    }

    def parse_options(self, opt, stream):
        super(SubtitleCodec, self).parse_options(opt)
        stream = str(stream)
        safe = self.safe_options(opt)

        if 'forced' in safe:
            f = safe['forced']
            if f < 0 or f > 1:
                del safe['forced']

        if 'default' in safe:
            d = safe['default']
            if d < 0 or d > 1:
                del safe['default']

        if 'language' in safe:
            l = safe['language']
            if len(l) > 3:
                del safe['language']

        safe = self._codec_specific_parse_options(safe)

        optlist = ['-c:s:' + stream, self.ffmpeg_codec_name]
        if 'path' in safe:
            optlist.extend(['-i', str(safe['path'])])
        if 'source' in safe:
            s = str(safe['source'])
        else:
            s = str('0')
        if 'map' in safe:
            optlist.extend(['-map', s + ':' + str(safe['map'])])
        if 'default' in safe:
            optlist.extend(['-metadata:s:s:' + stream, "disposition:default=" + str(safe['default'])])
        if 'forced' in safe:
            optlist.extend(['-metadata:s:s:' + stream, "disposition:forced=" + str(safe['forced'])])
        if 'language' in safe:
                lang = str(safe['language'])
        else:
            lang = 'und'
        optlist.extend(['-metadata:s:s:' + stream, "language=" + lang])

        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))
        return optlist


class VideoCodec(BaseCodec):
    """
    Base video codec class handles general video options. Possible
    parameters are:
      * codec (string) - video codec name
      * bitrate (string) - stream bitrate
      * fps (integer) - frames per second
      * width (integer) - video width
      * height (integer) - video height
      * mode (string) - aspect preserval mode; one of:
            * stretch (default) - don't preserve aspect
            * crop - crop extra w/h
            * pad - pad with black bars
      * src_width (int) - source width
      * src_height (int) - source height

    Aspect preserval mode is only used if both source
    and both destination sizes are specified. If source
    dimensions are not specified, aspect settings are ignored.

    If source dimensions are specified, and only one
    of the destination dimensions is specified, the other one
    is calculated to preserve the aspect ratio.

    Supported video codecs are: null (no video), copy (copy directly
    from the source), Theora, H.264/AVC, DivX, VP8, H.263, Flv,
    MPEG-1, MPEG-2.
    """

    encoder_options = {
        'codec': str,
        'bitrate': int,
        'fps': int,
        'width': int,
        'height': int,
        'mode': str,
        'src_width': int,
        'src_height': int,
        'map': int
    }

    def _aspect_corrections(self, sw, sh, w, h, mode):
        # If we don't have source info, we don't try to calculate
        # aspect corrections
        if not sw or not sh:
            return (w, h, None)

        # Original aspect ratio
        aspect = (1.0 * sw) / (1.0 * sh)

        # If we have only one dimension, we can easily calculate
        # the other to match the source aspect ratio
        if not w and not h:
            return (w, h, None)
        elif w and not h:
            h = int((1.0 * w) / aspect)
            return (w, h, None)
        elif h and not w:
            w = int(aspect * h)
            return (w, h, None)

        # If source and target dimensions are actually the same aspect
        # ratio, we've got nothing to do
        if int(aspect * h) == w:
            return (w, h, None)

        if mode == 'stretch':
            return (w, h, None)

        target_aspect = (1.0 * w) / (1.0 * h)

        if mode == 'crop':
            # source is taller, need to crop top/bottom
            if target_aspect > aspect:  # target is taller
                h0 = int(w / aspect)
                assert h0 > h, (sw, sh, w, h)
                dh = (h0 - h) / 2
                return (w, h0, 'crop=0:%d:%d:%d' % (dh, w, h))
            else:  # source is wider, need to crop left/right
                w0 = int(h * aspect)
                assert w0 > w, (sw, sh, w, h)
                dw = (w0 - w) / 2
                return (w0, h, 'crop=%d:0:%d:%d' % (dw, w, h))

        if mode == 'pad':
            # target is taller, need to pad top/bottom
            if target_aspect < aspect:
                h1 = int(w / aspect)
                assert h1 < h, (sw, sh, w, h)
                dh = (h - h1) / 2
                return (w, h1, 'pad=%d:%d:0:%d' % (w, h, dh))
            else:  # target is wider, need to pad left/right
                w1 = int(h * aspect)
                assert w1 < w, (sw, sh, w, h)
                dw = (w - w1) / 2
                return (w1, h, 'pad=%d:%d:%d:0' % (w, h, dw))

        assert False, mode

    def parse_options(self, opt):
        super(VideoCodec, self).parse_options(opt)

        safe = self.safe_options(opt)

        if 'fps' in safe:
            f = safe['fps']
            if f < 1 or f > 120:
                del safe['fps']

        if 'bitrate' in safe:
            br = safe['bitrate']
            if br < 16 or br > 15000:
                del safe['bitrate']

        w = None
        h = None

        if 'width' in safe:
            w = safe['width']
            if w < 16 or w > 4000:
                w = None

        if 'height' in safe:
            h = safe['height']
            if h < 16 or h > 3000:
                h = None

        sw = None
        sh = None
        aspect = None

        if 'src_width' in safe and 'src_height' in safe:
            sw = safe['src_width']
            sh = safe['src_height']
            if not sw or not sh:
                sw = None
                sh = None
            else:
                aspect = (1.0 * sw) / (1.0 * sh)

        mode = 'stretch'
        if 'mode' in safe:
            if safe['mode'] in ['stretch', 'crop', 'pad']:
                mode = safe['mode']

        w, h, filters = self._aspect_corrections(sw, sh, w, h, mode)

        safe['width'] = w
        safe['height'] = h
        safe['aspect_filters'] = filters

        if w and h:
            safe['aspect'] = '%d:%d' % (w, h)

        safe = self._codec_specific_parse_options(safe)

        w = safe['width']
        h = safe['height']
        filters = safe['aspect_filters']

        optlist = ['-vcodec', self.ffmpeg_codec_name]
        if 'map' in safe:
            optlist.extend(['-map', '0:' + str(safe['map'])])
        if 'fps' in safe:
            optlist.extend(['-r', str(safe['fps'])])
        if 'bitrate' in safe:
            optlist.extend(['-b', str(safe['bitrate']) + 'k'])
        if w and h:
            optlist.extend(['-s', '%dx%d' % (w, h),
                '-aspect', '%d:%d' % (w, h)])
        if filters:
            optlist.extend(['-vf', filters])

        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))
        return optlist


class AudioNullCodec(BaseCodec):
    """
    Null audio codec (no audio).
    """
    codec_name = None

    def parse_options(self, opt, stream):
        return ['-an']


class VideoNullCodec(BaseCodec):
    """
    Null video codec (no video).
    """

    codec_name = None

    def parse_options(self, opt):
        return ['-vn']


class AudioCopyCodec(BaseCodec):
    """
    Copy audio stream directly from the source.
    """
    codec_name = 'copy'
    encoder_options = {'language': str,
                       'map': int}

    def parse_options(self, opt, stream):
        safe = self.safe_options(opt)
        stream = str(stream)
        optlist = []
        optlist.extend(['-c:a:' + stream, 'copy'])
        if 'map' in safe:
            optlist.extend(['-map', '0:' + str(safe['map'])])
        if 'language' in safe:
            l = safe['language']
            if len(l) > 3:
                del safe['language']
            else:
                lang = str(safe['language'])
        else:
            lang = 'und'
        optlist.extend(['-metadata:s:a:' + stream, "language=" + lang])
        return optlist


class VideoCopyCodec(BaseCodec):
    """
    Copy video stream directly from the source.
    """
    codec_name = 'copy'
    encoder_options = {'map': int}

    def parse_options(self, opt):
        safe = self.safe_options(opt)
        optlist = []
        optlist.extend(['-vcodec', 'copy'])
        if 'map' in safe:
            optlist.extend(['-map', '0:' + str(safe['map'])])
        return optlist


class VorbisCodec(AudioCodec):
    """
    Vorbis audio codec.
    """
    codec_name = 'vorbis'
    ffmpeg_codec_name = 'libvorbis'


class TheoraCodec(VideoCodec):
    """
    Theora video codec.
    """
    codec_name = 'theora'
    ffmpeg_codec_name = 'libtheora'


class AacCodec(AudioCodec):
    """
    AAC audio codec.
    """
    codec_name = 'aac'
    ffmpeg_codec_name = 'aac'
    aac_experimental_enable = ['-strict', 'experimental']

    def _codec_specific_produce_ffmpeg_list(self, safe):
        return self.aac_experimental_enable


class Ac3Codec(AudioCodec):
    """
    AC3 audio codec
    """
    codec_name = 'ac3'
    ffmpeg_codec_name = 'ac3'


class DtsCodec(AudioCodec):
    """
    AC3 audio codec
    """
    codec_name = 'dts'
    ffmpeg_codec_name = 'dts'


class H264Codec(VideoCodec):
    """
    H.264/AVC video codec.
    """
    codec_name = 'h264'
    ffmpeg_codec_name = 'libx264'

    x264_voodoo_recipe_ipod = ("-flags +loop -cmp +chroma " +
        "-partitions +parti4x4+partp8x8+partb8x8 -subq 5 -trellis 1 " +
        "-refs 1 -coder 0 -me_range 16 -g 300 -keyint_min 25 " +
        "-sc_threshold 40 -i_qfactor 0.71 -rc_eq 'blurCplx^(1-qComp)' " +
        "-qcomp 0.6 -qmin 10 -qmax 51 -qdiff 4 -level 30")

    #def _codec_specific_produce_ffmpeg_list(self, safe):
        #return self.x264_voodoo_recipe_ipod.split(' ')


class Mp3Codec(AudioCodec):
    """
    MP3 (MPEG layer 3) audio codec.
    """
    codec_name = 'mp3'
    ffmpeg_codec_name = 'libmp3lame'


class Mp2Codec(AudioCodec):
    """
    MP2 (MPEG layer 2) audio codec.
    """
    codec_name = 'mp2'
    ffmpeg_codec_name = 'mp2'


class DivxCodec(VideoCodec):
    """
    DivX video codec.
    """
    codec_name = 'divx'
    ffmpeg_codec_name = 'mpeg4'


class Vp8Codec(VideoCodec):
    """
    Google VP8 video codec.
    """
    codec_name = 'vp8'
    ffmpeg_codec_name = 'vp8'


class H263Codec(VideoCodec):
    """
    H.263 video codec.
    """
    codec_name = 'h263'
    ffmpeg_codec_name = 'h263'


class FlvCodec(VideoCodec):
    """
    Flash Video codec.
    """
    codec_name = 'flv'
    ffmpeg_codec_name = 'flv'


class MpegCodec(VideoCodec):
    """
    Base MPEG video codec.
    """
    # Workaround for a bug in ffmpeg in which aspect ratio
    # is not correctly preserved, so we have to set it
    # again in vf; take care to put it *before* crop/pad, so
    # it uses the same adjusted dimensions as the codec itself
    # (pad/crop will adjust it further if neccessary)
    def _codec_specific_parse_options(self, safe):
        w = safe['width']
        h = safe['height']

        if w and h:
            filters = safe['aspect_filters']
            tmp = 'aspect=%d:%d' % (w, h)

            if filters is None:
                safe['aspect_filters'] = tmp
            else:
                safe['aspect_filters'] = tmp + ',' + filters

        return safe


class Mpeg1Codec(MpegCodec):
    """
    MPEG-1 video codec.
    """
    codec_name = 'mpeg1'
    ffmpeg_codec_name = 'mpeg1video'


class Mpeg2Codec(MpegCodec):
    """
    MPEG-2 video codec.
    """
    codec_name = 'mpeg2'
    ffmpeg_codec_name = 'mpeg2video'


class MOVTextCodec(SubtitleCodec):
    """
    MOV Text video codec.
    """
    codec_name = 'mov_text'
    ffmpeg_codec_name = 'mov_text'


audio_codec_list = [
    AudioNullCodec, AudioCopyCodec, VorbisCodec, AacCodec, Mp3Codec, Mp2Codec, Ac3Codec, DtsCodec
]

video_codec_list = [
    VideoNullCodec, VideoCopyCodec, TheoraCodec, H264Codec,
    DivxCodec, Vp8Codec, H263Codec, FlvCodec, Mpeg1Codec,
    Mpeg2Codec
]

subtitle_codec_list = [
    MOVTextCodec
]
