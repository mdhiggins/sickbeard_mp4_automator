#!/usr/bin/env python3


class BaseCodec(object):
    """
    Base audio/video/subtitle codec class.
    """
    DISPOSITIONS = [
        'default',
        'dub',
        'original',
        'comment',
        'lyrics',
        'karaoke',
        'forced',
        'hearing_impaired',
        'visual_impaired',
        # 'clean_effects',
        # 'attached_pic',
        'captions',
        # 'descriptions',
        # 'dependent',
        # 'metadata',
    ]

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

    def safe_disposition(self, dispo):
        dispo = dispo or ""
        for d in self.DISPOSITIONS:
            if d not in dispo:
                dispo += '-' + d
        return dispo

    def safe_options(self, opts):
        safe = {}

        # Only copy options that are expected and of correct type
        # (and do typecasting on them)
        for k, v in opts.items():
            if k in self.encoder_options and v is not None:
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
      * language (string) - language of audio stream (3 char code)
      * map (int) - stream index
      * disposition (string) - disposition string (+default+forced)

    Supported audio codecs are: null (no audio), copy (copy from
    original), vorbis, aac, mp3, mp2
    """

    encoder_options = {
        'codec': str,
        'language': str,
        'title': str,
        'channels': int,
        'bitrate': int,
        'samplerate': int,
        'source': int,
        'path': str,
        'filter': str,
        'map': int,
        'disposition': str,
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

        if 'filter' in safe:
            x = safe['filter']
            if len(x) < 1:
                del safe['filter']

        if 'disposition' in safe:
            if len(safe['disposition'].strip()) < 1:
                del safe['disposition']

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
            optlist.extend(['-metadata:s:a:' + stream, 'BPS=' + str(br * 1000)])
            optlist.extend(['-metadata:s:a:' + stream, 'BPS-eng=' + str(br * 1000)])
        if 'samplerate' in safe:
            optlist.extend(['-ar:a:' + stream, str(safe['samplerate'])])
        if 'filter' in safe:
            optlist.extend(['-filter:a:' + stream, str(safe['filter'])])
        if 'title' in safe:
            optlist.extend(['-metadata:s:a:' + stream, "title=" + str(safe['title'])])
        if 'language' in safe:
            lang = str(safe['language'])
        else:
            lang = 'und'  # Never leave blank if not specified, always set to und for undefined
        optlist.extend(['-metadata:s:a:' + stream, "language=" + lang])
        optlist.extend(['-disposition:a:' + stream, self.safe_disposition(safe.get('dispo'))])

        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))
        return optlist


class SubtitleCodec(BaseCodec):
    """
    Base subtitle codec class handles general subtitle options. Possible
    parameters are:
      * codec (string) - subtitle codec name (mov_text, subrib, ssa only supported currently)
      * language (string) - language of subtitle stream (3 char code)
      * disposition (string) - disposition as string (+default+forced)

    Supported subtitle codecs are: null (no subtitle), mov_text
    """

    encoder_options = {
        'codec': str,
        'language': str,
        'title': str,
        'map': int,
        'source': int,
        'path': str,
        'encoding': str,
        'disposition': str,
    }

    def parse_options(self, opt, stream=0):
        super(SubtitleCodec, self).parse_options(opt)
        stream = str(stream)
        safe = self.safe_options(opt)

        if 'language' in safe:
            l = safe['language']
            if len(l) > 3:
                del safe['language']

        if 'source' in safe:
            s = str(safe['source'])
        else:
            s = str(0)

        if 'encoding' in safe:
            if not safe['encoding']:
                del safe['encoding']

        if 'disposition' in safe:
            if len(safe['disposition'].strip()) < 1:
                del safe['disposition']

        safe = self._codec_specific_parse_options(safe)

        optlist = []
        if 'encoding' in safe:
            optlist.extend(['-sub_charenc', str(safe['encoding'])])
        optlist.extend(['-c:s:' + stream, self.ffmpeg_codec_name])
        stream = str(stream)
        if 'map' in safe:
            optlist.extend(['-map', s + ':' + str(safe['map'])])
        if 'path' in safe:
            optlist.extend(['-i', str(safe['path'])])
        if 'title' in safe:
            optlist.extend(['-metadata:s:s:' + stream, "title=" + str(safe['title'])])
        if 'language' in safe:
            lang = str(safe['language'])
        else:
            lang = 'und'  # Never leave blank if not specified, always set to und for undefined
        optlist.extend(['-metadata:s:s:' + stream, "language=" + lang])
        optlist.extend(['-disposition:s:' + stream, self.safe_disposition(safe.get('dispo'))])

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
        'crf': int,
        'maxrate': str,
        'bufsize': str,
        'fps': float,
        'width': int,
        'height': int,
        'mode': str,
        'src_width': int,
        'src_height': int,
        'filter': str,
        'pix_fmt': str,
        'field_order': str,
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
            return w, h, None
        elif h and not w:
            w = int(aspect * h)
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
            if f < 1:
                del safe['fps']

        if 'bitrate' in safe:
            bitrate = safe['bitrate']
            if bitrate < 1:
                del safe['bitrate']

        if 'crf' in safe:
            crf = safe['crf']
            if crf < 0 or crf > 51:
                del safe['crf']

        if 'field_order' in safe:
            if safe['field_order'] not in ['progressive', 'tt', 'bb', 'tb', 'bt']:
                del safe['field_order']

        w = None
        h = None

        if 'width' in safe:
            w = safe['width']
            if w < 16:
                del safe['width']
                w = None

        if 'height' in safe:
            h = safe['height']
            if h < 16:
                del safe['height']
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

        w = safe.get('width', None)
        h = safe.get('height', None)
        filters = safe.get('aspect_filters', None)

        optlist = ['-vcodec', self.ffmpeg_codec_name]
        if 'map' in safe:
            optlist.extend(['-map', '0:' + str(safe['map'])])
        if 'fps' in safe:
            optlist.extend(['-r:v', str(safe['fps'])])
        if 'pix_fmt' in safe:
            optlist.extend(['-pix_fmt', str(safe['pix_fmt'])])
        if 'field_order' in safe:
            optlist.extend(['-field_order', str(safe['field_order'])])
        # CRF gets priority over bitrate, but if bitrate is present without maxrate, use bitrate as maxrate
        if 'crf' in safe:
            optlist.extend(['-crf', str(safe['crf'])])
            if 'maxrate' in safe:
                optlist.extend(['-maxrate:v', str(safe['maxrate'])])
            elif 'bitrate' in safe:
                optlist.extend(['-maxrate:v', str(safe['bitrate']) + 'k'])
            if 'bufsize' in safe:
                optlist.extend(['-bufsize', str(safe['bufsize'])])
        elif 'bitrate' in safe:
            optlist.extend(['-vb', str(safe['bitrate']) + 'k'])
        if 'bitrate' in safe:
            optlist.extend(['-metadata:s:v', 'BPS=' + str(safe['bitrate'] * 1000)])
            optlist.extend(['-metadata:s:v', 'BPS-eng=' + str(safe['bitrate'] * 1000)])
        if 'filter' in safe:
            optlist.extend(['-vf', str(safe['filter'])])
        if filters:
            optlist.extend(['-vf', filters])
        if w and h:
            optlist.extend(['-s', '%dx%d' % (w, h)])
            if ow and oh:
                optlist.extend(['-aspect', '%d:%d' % (ow, oh)])

        optlist.extend(self._codec_specific_produce_ffmpeg_list(safe))

        # consolidate filters
        if optlist.count('-vf') > 1:
            vf = []
            while optlist.count('-vf') > 0:
                vf.append(optlist.pop(optlist.index('-vf') + 1))
                del optlist[optlist.index('-vf')]

            vfstring = ""
            for line in vf:
                vfstring = "%s,%s" % (vfstring, line)

            optlist.extend(['-vf', vfstring[1:]])

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
    encoder_options = {'map': int,
                       'source': str,
                       'bsf': str,
                       'disposition': str,
                       'language': str,
                       'title': str}

    def parse_options(self, opt, stream=0):
        safe = self.safe_options(opt)

        if 'disposition' in safe:
            if len(safe['disposition'].strip()) < 1:
                del safe['disposition']

        if 'language' in safe:
            l = safe['language']
            if len(l) > 3:
                del safe['language']

        stream = str(stream)
        optlist = []
        optlist.extend(['-c:a:' + stream, 'copy'])
        if 'source' in safe:
            s = str(safe['source'])
        else:
            s = str(0)
        if 'map' in safe:
            optlist.extend(['-map', s + ':' + str(safe['map'])])
        if 'bsf' in safe:
            optlist.extend(['-bsf:a:' + stream, str(safe['bsf'])])
        if 'title' in safe:
            optlist.extend(['-metadata:s:a:' + stream, "title=" + str(safe['title'])])
        if 'language' in safe:
            lang = str(safe['language'])
        else:
            lang = 'und'
        optlist.extend(['-metadata:s:a:' + stream, "language=" + lang])
        optlist.extend(['-disposition:a:' + stream, self.safe_disposition(safe.get('dispo'))])
        return optlist


class VideoCopyCodec(BaseCodec):
    """
    Copy video stream directly from the source.
    """
    codec_name = 'copy'
    encoder_options = {'map': int,
                       'source': str,
                       'fps': float}

    def parse_options(self, opt, stream=0):
        safe = self.safe_options(opt)
        optlist = []
        optlist.extend(['-vcodec', 'copy'])

        if 'fps' in safe:
            f = safe['fps']
            if f < 1:
                del safe['fps']

        if 'source' in safe:
            s = str(safe['source'])
        else:
            s = str(0)
        if 'map' in safe:
            optlist.extend(['-map', s + ':' + str(safe['map'])])
        if 'fps' in safe:
            optlist.extend(['-r:v', str(safe['fps'])])
        return optlist


class SubtitleCopyCodec(BaseCodec):
    """
    Copy subtitle stream directly from the source.
    """
    codec_name = 'copy'
    encoder_options = {'map': int,
                       'source': str,
                       'disposition': str,
                       'language': str,
                       'title': str}

    optlist = []

    def parse_options(self, opt, stream=0):
        safe = self.safe_options(opt)

        if 'disposition' in safe:
            if len(safe['disposition'].strip()) < 1:
                del safe['disposition']

        if 'language' in safe:
            l = safe['language']
            if len(l) > 3:
                del safe['language']

        stream = str(stream)
        optlist = []
        optlist.extend(['-c:s:' + stream, 'copy'])
        if 'source' in safe:
            s = str(safe['source'])
        else:
            s = str(0)
        if 'map' in safe:
            optlist.extend(['-map', s + ':' + str(safe['map'])])
        if 'title' in safe:
            optlist.extend(['-metadata:s:s:' + stream, "title=" + str(safe['title'])])
        if 'language' in safe:
            lang = str(safe['language'])
        else:
            lang = 'und'
        optlist.extend(['-metadata:s:s:' + stream, "language=" + lang])
        optlist.extend(['-disposition:s:' + stream, self.safe_disposition(safe.get('dispo'))])

        return optlist


class AttachmentCopyCodec(BaseCodec):
    """
    Copy attachment stream directly from the source.
    """
    codec_name = 'copy'
    encoder_options = {'map': int,
                       'source': str}

    optlist = []

    def parse_options(self, opt, stream=0):
        safe = self.safe_options(opt)

        stream = str(stream)
        optlist = []
        optlist.extend(['-c:t:' + stream, 'copy'])
        if 'source' in safe:
            s = str(safe['source'])
        else:
            s = str(0)
        if 'map' in safe:
            optlist.extend(['-map', s + ':' + str(safe['map'])])
        return optlist


# Audio Codecs
class VorbisCodec(AudioCodec):
    """
    Vorbis audio codec.
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

    def parse_options(self, opt, stream=0):
        if 'channels' in opt:
            c = opt['channels']
            if c > 6:
                opt['channels'] = 6
        return super(AacCodec, self).parse_options(opt, stream)

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        return self.aac_experimental_enable


class FdkAacCodec(AudioCodec):
    """
    AAC audio codec.
    """
    codec_name = 'libfdk_aac'
    ffmpeg_codec_name = 'libfdk_aac'

    def parse_options(self, opt, stream=0):
        if 'channels' in opt:
            c = opt['channels']
            if c > 6:
                opt['channels'] = 6
        return super(FdkAacCodec, self).parse_options(opt, stream)


class FAacCodec(AudioCodec):
    """
    AAC audio codec.
    """
    codec_name = 'libfaac'
    ffmpeg_codec_name = 'libfaac'

    def parse_options(self, opt, stream=0):
        if 'channels' in opt:
            c = opt['channels']
            if c > 6:
                opt['channels'] = 6
        return super(FAacCodec, self).parse_options(opt, stream)


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


class EAc3Codec(AudioCodec):
    """
    Dolby Digital Plus/EAC3 audio codec.
    """
    codec_name = 'eac3'
    ffmpeg_codec_name = 'eac3'

    def parse_options(self, opt, stream=0):
        if 'channels' in opt:
            c = opt['channels']
            if c > 8:
                opt['channels'] = 8
        if 'bitrate' in opt:
            br = opt['bitrate']
            if br > 640:
                opt['bitrate'] = 640
        return super(EAc3Codec, self).parse_options(opt, stream)


class FlacCodec(AudioCodec):
    """
    FLAC audio codec.
    """
    codec_name = 'flac'
    ffmpeg_codec_name = 'flac'
    flac_experimental_enable = ['-strict', 'experimental']

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        return self.flac_experimental_enable


class DtsCodec(AudioCodec):
    """
    DTS audio codec.
    """
    codec_name = 'dts'
    ffmpeg_codec_name = 'dts'
    dts_experimental_enable = ['-strict', 'experimental']

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        return self.dts_experimental_enable


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


class Opus(AudioCodec):
    """
    Opus audio codec
    """
    codec_name = 'opus'
    ffmpeg_codec_name = 'libopus'
    opus_experimental_enable = ['-strict', 'experimental']

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        return self.opus_experimental_enable


class PCMS24LE(AudioCodec):
    """
    PCM_S24LE Audio Codec
    """
    codec_name = 'pcm_s24le'
    ffmpeg_codec_name = 'pcm_s24le'


class PCMS16LE(AudioCodec):
    """
    PCM_S16LE Audio Codec
    """
    codec_name = 'pcm_s16le'
    ffmpeg_codec_name = 'pcm_s16le'


# Video Codecs
class TheoraCodec(VideoCodec):
    """
    Theora video codec.
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
    """
    codec_name = 'h264'
    ffmpeg_codec_name = 'libx264'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'preset': str,  # common presets are ultrafast, superfast, veryfast,
        # faster, fast, medium(default), slow, slower, veryslow
        'profile': str,  # default: not-set, for valid values see above link
        'level': float,  # default: not-set, values range from 3.0 to 4.2
        'tune': str,  # default: not-set, for valid values see above link
        'wscale': int,  # special handlers for the even number requirements of h264
        'hscale': int  # special handlers for the even number requirements of h264
    })
    scale_filter = 'scale'

    def _codec_specific_parse_options(self, safe, stream=0):
        if 'width' in safe and safe['width']:
            safe['width'] = 2 * round(safe['width'] / 2)
            safe['wscale'] = safe['width']
            del(safe['width'])
        if 'height' in safe and safe['height']:
            if safe['height'] % 2 == 0:
                safe['hscale'] = safe['height']
            del(safe['height'])
        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = []
        if 'level' in safe:
            if safe['level'] < 3.0 or safe['level'] > 4.2:
                del safe['level']

        if 'preset' in safe:
            optlist.extend(['-preset', safe['preset']])
        if 'profile' in safe:
            optlist.extend(['-profile:v', safe['profile']])
        if 'level' in safe:
            optlist.extend(['-level', '%0.1f' % safe['level']])
        if 'tune' in safe:
            optlist.extend(['-tune', safe['tune']])
        if 'wscale' in safe and 'hscale' in safe:
            optlist.extend(['-vf', '%s=%s:%s' % (self.scale_filter, safe['wscale'], safe['hscale'])])
        elif 'wscale' in safe:
            optlist.extend(['-vf', '%s=%s:trunc(ow/a/2)*2' % (self.scale_filter, safe['wscale'])])
        elif 'hscale' in safe:
            optlist.extend(['-vf', '%s=trunc((oh*a)/2)*2:%s' % (self.scale_filter, safe['hscale'])])
        return optlist


class NVEncH264(H264Codec):
    """
    Nvidia H.264/AVC video codec.
    """
    codec_name = 'h264_nvenc'
    ffmpeg_codec_name = 'h264_nvenc'
    scale_filter = 'scale_npp'


class VideotoolboxEncH264(H264Codec):
    """
    Videotoolbox H.264/AVC video codec.
    """
    codec_name = 'h264_videotoolbox'
    ffmpeg_codec_name = 'h264_videotoolbox'


class OMXH264(H264Codec):
    """
    OMX H.264/AVC video codec.
    """
    codec_name = 'h264_omx'
    ffmpeg_codec_name = 'h264_omx'


class H264VAAPI(H264Codec):
    """
    H.264/AVC VAAPI video codec.
    """
    codec_name = 'h264vaapi'
    ffmpeg_codec_name = 'h264_vaapi'
    scale_filter = 'scale_vaapi'

    def _codec_specific_parse_options(self, safe, stream=0):
        if 'width' in safe and safe['width']:
            safe['width'] = 2 * round(safe['width'] / 2)
            safe['vaapi_wscale'] = safe['width']
            del(safe['width'])
        if 'height' in safe and safe['height']:
            if safe['height'] % 2 == 0:
                safe['vaapi_hscale'] = safe['height']
            del(safe['height'])
        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = super(H264VAAPI, self)._codec_specific_produce_ffmpeg_list(safe, stream)
        optlist.extend(['-vaapi_device', '/dev/dri/renderD128'])
        if 'vaapi_wscale' in safe and 'vaapi_hscale' in safe:
            optlist.extend(['-vf', 'hwupload,%s=%s:%s:format=nv12' % (self.scale_filter, safe['vaapi_wscale'], safe['vaapi_hscale'])])
        elif 'vaapi_wscale' in safe:
            optlist.extend(['-vf', 'hwupload,%s=%s:trunc(ow/a/2)*2:format=nv12' % (self.scale_filter, safe['vaapi_wscale'])])
        elif 'vaapi_hscale' in safe:
            optlist.extend(['-vf', 'hwupload,%s=trunc((oh*a)/2)*2:%s:format=nv12' % (self.scale_filter, safe['vaapi_hscale'])])
        else:
            optlist.extend(['-vf', "format=nv12,hwupload"])

        return optlist


class H264QSV(H264Codec):
    """
    H.264/AVC video codec.
    """
    codec_name = 'h264qsv'
    ffmpeg_codec_name = 'h264_qsv'
    scale_filter = 'scale_qsv'

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = super(H264QSV, self)._codec_specific_produce_ffmpeg_list(safe, stream)
        optlist.extend(['-look_ahead', '0'])
        return optlist


class H265Codec(VideoCodec):
    """
    H.265/AVC video codec.
    """
    codec_name = 'h265'
    ffmpeg_codec_name = 'libx265'
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'preset': str,  # common presets are ultrafast, superfast, veryfast,
        # faster, fast, medium(default), slow, slower, veryslow
        'profile': str,  # default: not-set, for valid values see above link
        'level': float,  # default: not-set, values range from 3.0 to 4.2
        'tune': str,  # default: not-set, for valid values see above link
        'wscale': int,  # special handlers for the even number requirements of h265
        'hscale': int  # special handlers for the even number requirements of h265
    })
    scale_filter = 'scale'

    def _codec_specific_parse_options(self, safe, stream=0):
        if 'width' in safe and safe['width']:
            safe['width'] = 2 * round(safe['width'] / 2)
            safe['wscale'] = safe['width']
            del(safe['width'])
        if 'height' in safe and safe['height']:
            if safe['height'] % 2 == 0:
                safe['hscale'] = safe['height']
            del(safe['height'])
        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = []

        if 'preset' in safe:
            optlist.extend(['-preset', safe['preset']])
        if 'profile' in safe:
            optlist.extend(['-profile:v', safe['profile']])
        if 'level' in safe:
            optlist.extend(['-level', '%0.1f' % safe['level']])
        if 'tune' in safe:
            optlist.extend(['-tune', safe['tune']])
        if 'wscale' in safe and 'hscale' in safe:
            optlist.extend(['-vf', '%s=%s:%s' % (self.scale_filter, safe['wscale'], safe['hscale'])])
        elif 'wscale' in safe:
            optlist.extend(['-vf', '%s=%s:trunc(ow/a/2)*2' % (self.scale_filter, safe['wscale'])])
        elif 'hscale' in safe:
            optlist.extend(['-vf', '%s=trunc((oh*a)/2)*2:%s' % (self.scale_filter, safe['hscale'])])
        optlist.extend(['-tag:v', 'hvc1'])
        return optlist


class HEVCQSV(H265Codec):
    """
    HEVC video codec.
    """
    codec_name = 'hevcqsv'
    ffmpeg_codec_name = 'hevc_qsv'
    scale_filter = 'scale_qsv'


class H265VAAPI(H265Codec):
    """
    H.265/AVC VAAPI ideo codec.
    """
    codec_name = 'h265vaapi'
    ffmpeg_codec_name = 'hevc_vaapi'
    scale_filter = 'scale_vaapi'

    def _codec_specific_parse_options(self, safe, stream=0):
        if 'width' in safe and safe['width']:
            safe['width'] = 2 * round(safe['width'] / 2)
            safe['vaapi_wscale'] = safe['width']
            del(safe['width'])
        if 'height' in safe and safe['height']:
            if safe['height'] % 2 == 0:
                safe['vaapi_hscale'] = safe['height']
            del(safe['height'])
        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = super(H265VAAPI, self)._codec_specific_produce_ffmpeg_list(safe, stream)
        optlist.extend(['-vaapi_device', '/dev/dri/renderD128'])
        if 'vaapi_wscale' in safe and 'vaapi_hscale' in safe:
            optlist.extend(['-vf', 'hwupload,%s=%s:%s:format=nv12' % (self.scale_filter, safe['vaapi_wscale'], safe['vaapi_hscale'])])
        elif 'vaapi_wscale' in safe:
            optlist.extend(['-vf', 'hwupload,%s=%s:trunc(ow/a/2)*2:format=nv12' % (self.scale_filter, safe['vaapi_wscale'])])
        elif 'vaapi_hscale' in safe:
            optlist.extend(['-vf', 'hwupload,%s=trunc((oh*a)/2)*2:%s:format=nv12' % (self.scale_filter, safe['vaapi_hscale'])])
        else:
            optlist.extend(['-vf', "format=nv12,hwupload"])

        return optlist


class NVEncH265(H265Codec):
    """
    Nvidia H.265/AVC video codec.
    """
    codec_name = 'h265_nvenc'
    ffmpeg_codec_name = 'hevc_nvenc'
    scale_filter = 'scale_npp'


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


class PGSCodec(SubtitleCodec):
    """
    PGS subtitle codec.
    """
    codec_name = 'pgs'
    ffmpeg_codec_name = 'copy'


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
    FdkAacCodec, FAacCodec, EAc3Codec, Ac3Codec, DtsCodec, FlacCodec, Opus, PCMS24LE, PCMS16LE
]

video_codec_list = [
    VideoNullCodec, VideoCopyCodec, TheoraCodec, H264Codec, H264QSV, HEVCQSV, H265Codec,
    DivxCodec, Vp8Codec, H263Codec, FlvCodec, Mpeg1Codec, NVEncH264, NVEncH265,
    Mpeg2Codec, H264VAAPI, H265VAAPI, OMXH264, VideotoolboxEncH264
]

subtitle_codec_list = [
    SubtitleNullCodec, SubtitleCopyCodec, MOVTextCodec, SrtCodec, SSA, SubRip, DVDSub,
    DVBSub, WebVTTCodec, PGSCodec
]

attachment_codec_list = [
    AttachmentCopyCodec
]
