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

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
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
        'source': int,
        'path' : str,
        'filter' : str,
        'map': int
    }

    def parse_options(self, opt, stream=0):
        super(AudioCodec, self).parse_options(opt)
        safe = self.safe_options(opt)
        stream = str(stream)

        if 'channels' in safe:
            c = safe['channels']
            if c < 1 or c > 12:
                del safe['channels']

        if 'bitrate' in safe:
            br = safe['bitrate']
            if br < 8:
                br = 8
            if br > 1536:
                br = 1536

        if 'samplerate' in safe:
            f = safe['samplerate']
            if f < 1000 or f > 50000:
                del safe['samplerate']

        if 'language' in safe:
            l = safe['language']
            if len(l) > 3:
                del safe['language']

        if 'source' in safe:
            s = str(safe['source'])
        else:
            s = str(0)

        safe = self._codec_specific_parse_options(safe)
        optlist = []
        optlist.extend(['-c:a:' + stream, self.ffmpeg_codec_name])
        if 'path' in safe:
            optlist.extend(['-i', str(safe['path'])])
        if 'map' in safe:
            optlist.extend(['-map', s + ':' + str(safe['map'])])
        if 'channels' in safe:
            optlist.extend(['-ac:a:' + stream, str(safe['channels'])])
        if 'bitrate' in safe:
            optlist.extend(['-b:a:' + stream, str(br) + 'k'])
        if 'samplerate' in safe:
            optlist.extend(['-ar:a:' + stream, str(safe['samplerate'])])
        if 'filter' in safe:
            optlist.extend(['-filter:a:' + stream, str(safe['filter'])])
        if 'language' in safe:
                lang = str(safe['language'])
        else:
            lang = 'und' # Never leave blank if not specified, always set to und for undefined
        optlist.extend(['-metadata:s:a:' + stream, "language=" + lang])

        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))
        return optlist


class SubtitleCodec(BaseCodec):
    """
    Base subtitle codec class handles general subtitle options. Possible
    parameters are:
      * codec (string) - subtitle codec name (mov_text, subrib, ssa only supported currently)
      * language (string) - language of subtitle stream (3 char code)
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

    def parse_options(self, opt, stream=0):
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

        if 'source' in safe:
            s = str(safe['source'])
        else:
            s = str(0)

        safe = self._codec_specific_parse_options(safe)

        optlist = []
        optlist.extend(['-c:s:' + stream, self.ffmpeg_codec_name])
        stream = str(stream)
        if 'map' in safe:
            optlist.extend(['-map', s + ':' + str(safe['map'])])
        if 'path' in safe:
            optlist.extend(['-i', str(safe['path'])])
        if 'default' in safe:
            optlist.extend(['-metadata:s:s:' + stream, "disposition:default=" + str(safe['default'])])
        if 'forced' in safe:
            optlist.extend(['-metadata:s:s:' + stream, "disposition:forced=" + str(safe['forced'])])
        if 'language' in safe:
                lang = str(safe['language'])
        else:
            lang = 'und' # Never leave blank if not specified, always set to und for undefined
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
        'filter': str,
        'map': int
    }

    def _aspect_corrections(self, sw, sh, w, h, mode):
        # If we don't have source info, we don't try to calculate
        # aspect corrections
        if not sw or not sh:
            return w, h, None

        # Original aspect ratio
        aspect = (1.0 * sw) / (1.0 * sh)

        # If we have only one dimension, we can easily calculate
        # the other to match the source aspect ratio
        if not w and not h:
            return w, h, None
        elif w and not h:
            h = int((1.0 * w) / aspect)
            h = (round(h/2))*2
            w = (round((h * aspect)/2))*2
            return w, h, None
        elif h and not w:
            w = int(aspect * h)
            w = (round(w)/2)*2
            h = (round((w * aspect)/2))*2
            return w, h, None

        # If source and target dimensions are actually the same aspect
        # ratio, we've got nothing to do
        if int(aspect * h) == w:
            return w, h, None

        if mode == 'stretch':
            return w, h, None

        target_aspect = (1.0 * w) / (1.0 * h)

        if mode == 'crop':
            # source is taller, need to crop top/bottom
            if target_aspect > aspect:  # target is taller
                h0 = int(w / aspect)
                assert h0 > h, (sw, sh, w, h)
                dh = (h0 - h) / 2
                return w, h0, 'crop=%d:%d:0:%d' % (w, h, dh)
            else:  # source is wider, need to crop left/right
                w0 = int(h * aspect)
                assert w0 > w, (sw, sh, w, h)
                dw = (w0 - w) / 2
                return w0, h, 'crop=%d:%d:%d:0' % (w, h, dw)

        if mode == 'pad':
            # target is taller, need to pad top/bottom
            if target_aspect < aspect:
                h1 = int(w / aspect)
                assert h1 < h, (sw, sh, w, h)
                dh = (h - h1) / 2
                return w, h1, 'pad=%d:%d:0:%d' % (w, h, dh)  # FIXED
            else:  # target is wider, need to pad left/right
                w1 = int(h * aspect)
                assert w1 < w, (sw, sh, w, h)
                dw = (w - w1) / 2
                return w1, h, 'pad=%d:%d:%d:0' % (w, h, dw)  # FIXED

        assert False, mode

    def parse_options(self, opt, stream=0):
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

        if 'src_width' in safe and 'src_height' in safe:
            sw = safe['src_width']
            sh = safe['src_height']
            if not sw or not sh:
                sw = None
                sh = None

        mode = 'stretch'
        if 'mode' in safe:
            if safe['mode'] in ['stretch', 'crop', 'pad']:
                mode = safe['mode']

        ow, oh = w, h  # FIXED
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
            optlist.extend(['-vb', str(safe['bitrate']) + 'k'])  # FIXED
        if 'filter' in safe:
            if filters:
                filters = '%s;%s' % (filters, str(safe['filter']))
            else:
                filters = str(safe['filter'])
        if w and h:
            optlist.extend(['-s', '%dx%d' % (w, h)])

            if ow and oh:
                optlist.extend(['-aspect', '%d:%d' % (ow, oh)])

        if filters:
            optlist.extend(['-vf', filters])

        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))
        return optlist


class AudioNullCodec(BaseCodec):
    """
    Null audio codec (no audio).
    """
    codec_name = None

    def parse_options(self, opt, stream=0):
        return ['-an']


class VideoNullCodec(BaseCodec):
    """
    Null video codec (no video).
    """

    codec_name = None

    def parse_options(self, opt):
        return ['-vn']


class SubtitleNullCodec(BaseCodec):
    """
    Null subtitle codec (no subtitle)
    """

    codec_name = None

    def parse_options(self, opt, stream=0):
        return ['-sn']


class AudioCopyCodec(BaseCodec):
    """
    Copy audio stream directly from the source.
    """
    codec_name = 'copy'
    encoder_options = {'language': str,
                       'source': str,
                       'map': int}

    def parse_options(self, opt, stream=0):
        safe = self.safe_options(opt)
        stream = str(stream)
        optlist = []
        optlist.extend(['-c:a:' + stream, 'copy'])
        if 'source' in safe:
            s = str(safe['source'])
        else:
            s = str(0)
        if 'map' in safe:
            optlist.extend(['-map', s + ':' + str(safe['map'])])
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
    encoder_options = {'map': int,
                       'source': str}

    def parse_options(self, opt, stream=0):
        safe = self.safe_options(opt)
        optlist = []
        optlist.extend(['-vcodec', 'copy'])
        if 'source' in safe:
            s = str(safe['source'])
        else:
            s = str(0)
        if 'map' in safe:
            optlist.extend(['-map', s + ':' + str(safe['map'])])
        return optlist


class SubtitleCopyCodec(BaseCodec):
    """
    Copy subtitle stream directly from the source.
    """
    codec_name = 'copy'
    encoder_options = {'map': int,
                       'source': str}

    optlist = []
    def parse_options(self, opt, stream=0):
        safe = self.safe_options(opt)
        stream = str(stream)
        if 'source' in safe:
            s = str(safe['source'])
        else:
            s = str(0)
        if 'map' in safe:
            optlist.extend(['-map', s + ':' + str(safe['map'])])
        optlist.extend(['-c:s:' + stream, copy])
        return optlist

# Audio Codecs
class VorbisCodec(AudioCodec):
    """
    Vorbis audio codec.
    @see http://ffmpeg.org/trac/ffmpeg/wiki/TheoraVorbisEncodingGuide
    """
    codec_name = 'vorbis'
    ffmpeg_codec_name = 'libvorbis'
    encoder_options = AudioCodec.encoder_options.copy()
    encoder_options.update({
        'quality': int,  # audio quality. Range is 0-10(highest quality)
        # 3-6 is a good range to try. Default is 3
    })

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = []
        stream = str(stream)
        if 'quality' in safe:
            optlist.extend(['-qscale:a:' + stream, safe['quality']])
        return optlist


class AacCodec(AudioCodec):
    """
    AAC audio codec.
    """
    codec_name = 'aac'
    ffmpeg_codec_name = 'aac'
    aac_experimental_enable = ['-strict', 'experimental']

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        return self.aac_experimental_enable


class FdkAacCodec(AudioCodec):
    """
    AAC audio codec.
    """
    codec_name = 'libfdk_aac'
    ffmpeg_codec_name = 'libfdk_aac'


class Ac3Codec(AudioCodec):
    """
    AC3 audio codec.
    """
    codec_name = 'ac3'
    ffmpeg_codec_name = 'ac3'

    def parse_options(self, opt, stream=0):
        if 'channels' in opt:
            c = opt['channels']
            if c > 6:
                opt['channels'] = 6
        return super(Ac3Codec, self).parse_options(opt, stream)


class FlacCodec(AudioCodec):
    """
    FLAC audio codec.
    """
    codec_name = 'flac'
    ffmpeg_codec_name = 'flac'


class DtsCodec(AudioCodec):
    """
    DTS audio codec.
    """
    codec_name = 'dts'
    ffmpeg_codec_name = 'dts'


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


# Video Codecs
class TheoraCodec(VideoCodec):
    """
    Theora video codec.
    @see http://ffmpeg.org/trac/ffmpeg/wiki/TheoraVorbisEncodingGuide
    """
    codec_name = 'theora'
    ffmpeg_codec_name = 'libtheora'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'quality': int,  # audio quality. Range is 0-10(highest quality)
        # 5-7 is a good range to try (default is 200k bitrate)
    })

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = []
        if 'quality' in safe:
            optlist.extend(['-qscale:v', safe['quality']])
        return optlist


class H264Codec(VideoCodec):
    """
    H.264/AVC video codec.
    @see http://ffmpeg.org/trac/ffmpeg/wiki/x264EncodingGuide
    """
    codec_name = 'h264'
    ffmpeg_codec_name = 'libx264'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'preset': str,  # common presets are ultrafast, superfast, veryfast,
        # faster, fast, medium(default), slow, slower, veryslow
        'quality': int,  # constant rate factor, range:0(lossless)-51(worst)
        # default:23, recommended: 18-28
        # http://mewiki.project357.com/wiki/X264_Settings#profile
        'profile': str,  # default: not-set, for valid values see above link
        'level': float, # default: not-set, values range from 3.0 to 4.2
        'tune': str,  # default: not-set, for valid values see above link
    })

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = []
        if 'preset' in safe:
            optlist.extend(['-preset', safe['preset']])
        if 'quality' in safe:
            optlist.extend(['-crf', safe['quality']])
        if 'profile' in safe:
            optlist.extend(['-profile:v', safe['profile']])
        if 'level' in safe:
            optlist.extend(['-level'], '%0.1f' % safe['level'])
        if 'tune' in safe:
            optlist.extend(['-tune', safe['tune']])
        return optlist


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
    ffmpeg_codec_name = 'libvpx'


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
    def _codec_specific_parse_options(self, safe, stream=0):
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


# Subtitle Codecs
class MOVTextCodec(SubtitleCodec):
    """
    mov_text subtitle codec.
    """
    codec_name = 'mov_text'
    ffmpeg_codec_name = 'mov_text'


class SrtCodec(SubtitleCodec):
    """
    SRT subtitle codec.
    """
    codec_name = 'srt'
    ffmpeg_codec_name = 'srt'


class WebVTTCodec(SubtitleCodec):
    """
    SRT subtitle codec.
    """
    codec_name = 'webvtt'
    ffmpeg_codec_name = 'webvtt'

class SSA(SubtitleCodec):
    """
    SSA (SubStation Alpha) subtitle.
    """
    codec_name = 'ass'
    ffmpeg_codec_name = 'ass'


class SubRip(SubtitleCodec):
    """
    SubRip subtitle.
    """
    codec_name = 'subrip'
    ffmpeg_codec_name = 'subrip'


class DVBSub(SubtitleCodec):
    """
    DVB subtitles.
    """
    codec_name = 'dvbsub'
    ffmpeg_codec_name = 'dvbsub'


class DVDSub(SubtitleCodec):
    """
    DVD subtitles.
    """
    codec_name = 'dvdsub'
    ffmpeg_codec_name = 'dvdsub'


audio_codec_list = [
    AudioNullCodec, AudioCopyCodec, VorbisCodec, AacCodec, Mp3Codec, Mp2Codec,
    FdkAacCodec, Ac3Codec, DtsCodec, FlacCodec
]

video_codec_list = [
    VideoNullCodec, VideoCopyCodec, TheoraCodec, H264Codec,
    DivxCodec, Vp8Codec, H263Codec, FlvCodec, Mpeg1Codec,
    Mpeg2Codec
]

subtitle_codec_list = [
    SubtitleNullCodec, SubtitleCopyCodec, MOVTextCodec, SrtCodec, SSA, SubRip, DVDSub,
    DVBSub, WebVTTCodec
]
