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
    ffprobe_codec_name = None

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

    def safe_framedata(self, opts):
        safe = ""
        return safe

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
        'sample_fmt': str,
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

        br = None
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

        if 'title' in safe:
            if len(safe['title']) < 1:
                del safe['title']

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
        if 'sample_fmt' in safe:
            optlist.extend(['-sample_fmt:a:' + stream, str(safe['sample_fmt'])])
        if 'filter' in safe:
            optlist.extend(['-filter:a:' + stream, str(safe['filter'])])
        if 'title' in safe:
            optlist.extend(['-metadata:s:a:' + stream, "title=" + str(safe['title'])])
            optlist.extend(['-metadata:s:a:' + stream, "handler_name=" + str(safe['title'])])
        else:
            optlist.extend(['-metadata:s:a:' + stream, "title="])
            optlist.extend(['-metadata:s:a:' + stream, "handler_name="])
        if 'language' in safe:
            lang = str(safe['language'])
        else:
            lang = 'und'  # Never leave blank if not specified, always set to und for undefined
        optlist.extend(['-metadata:s:a:' + stream, "language=" + lang])
        optlist.extend(['-disposition:a:' + stream, self.safe_disposition(safe.get('disposition'))])

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

        if 'disposition' in safe:
            if len(safe['disposition'].strip()) < 1:
                del safe['disposition']

        if 'title' in safe:
            if len(safe['title']) < 1:
                del safe['title']

        safe = self._codec_specific_parse_options(safe)

        optlist = []
        optlist.extend(['-c:s:' + stream, self.ffmpeg_codec_name])
        stream = str(stream)
        if 'map' in safe:
            optlist.extend(['-map', s + ':' + str(safe['map'])])
        if 'path' in safe:
            optlist.extend(['-i', str(safe['path'])])
        if 'title' in safe:
            optlist.extend(['-metadata:s:s:' + stream, "title=" + str(safe['title'])])
            optlist.extend(['-metadata:s:s:' + stream, "handler_name=" + str(safe['title'])])
        else:
            optlist.extend(['-metadata:s:s:' + stream, "title="])
            optlist.extend(['-metadata:s:s:' + stream, "handler_name="])
        if 'language' in safe:
            lang = str(safe['language'])
        else:
            lang = 'und'  # Never leave blank if not specified, always set to und for undefined
        optlist.extend(['-metadata:s:s:' + stream, "language=" + lang])
        optlist.extend(['-disposition:s:' + stream, self.safe_disposition(safe.get('disposition'))])

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
        'title': str,
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

        if 'title' in safe:
            if len(safe['title']) < 1:
                del safe['title']

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
        if 'title' in safe:
            optlist.extend(['-metadata:s:v', "title=" + str(safe['title'])])
            optlist.extend(['-metadata:s:v', "handler_name=" + str(safe['title'])])
        else:
            optlist.extend(['-metadata:s:v', "title="])
            optlist.extend(['-metadata:s:v', "handler_name="])

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

        if 'title' in safe:
            if len(safe['title']) < 1:
                del safe['title']

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
            optlist.extend(['-metadata:s:a:' + stream, "handler_name=" + str(safe['title'])])
        else:
            optlist.extend(['-metadata:s:a:' + stream, "title="])
            optlist.extend(['-metadata:s:a:' + stream, "handler_name="])
        if 'language' in safe:
            lang = str(safe['language'])
        else:
            lang = 'und'
        optlist.extend(['-metadata:s:a:' + stream, "language=" + lang])
        optlist.extend(['-disposition:a:' + stream, self.safe_disposition(safe.get('disposition'))])
        return optlist


class VideoCopyCodec(BaseCodec):
    """
    Copy video stream directly from the source.
    """
    codec_name = 'copy'
    encoder_options = {'map': int,
                       'source': str,
                       'fps': float,
                       'title': str}

    def parse_options(self, opt, stream=0):
        safe = self.safe_options(opt)
        optlist = []
        optlist.extend(['-vcodec', 'copy'])

        if 'fps' in safe:
            f = safe['fps']
            if f < 1:
                del safe['fps']

        if 'title' in safe:
            if len(safe['title']) < 1:
                del safe['title']

        if 'source' in safe:
            s = str(safe['source'])
        else:
            s = str(0)
        if 'map' in safe:
            optlist.extend(['-map', s + ':' + str(safe['map'])])
        if 'fps' in safe:
            optlist.extend(['-r:v', str(safe['fps'])])
        if 'title' in safe:
            optlist.extend(['-metadata:s:v', "title=" + str(safe['title'])])
            optlist.extend(['-metadata:s:v', "handler_name=" + str(safe['title'])])
        else:
            optlist.extend(['-metadata:s:v', "title="])
            optlist.extend(['-metadata:s:v', "handler_name="])
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

        if 'title' in safe:
            if len(safe['title']) < 1:
                del safe['title']

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
            optlist.extend(['-metadata:s:s:' + stream, "handler_name=" + str(safe['title'])])
        else:
            optlist.extend(['-metadata:s:s:' + stream, "title="])
            optlist.extend(['-metadata:s:s:' + stream, "handler_name="])
        if 'language' in safe:
            lang = str(safe['language'])
        else:
            lang = 'und'
        optlist.extend(['-metadata:s:s:' + stream, "language=" + lang])
        optlist.extend(['-disposition:s:' + stream, self.safe_disposition(safe.get('disposition'))])

        return optlist


class AttachmentCopyCodec(BaseCodec):
    """
    Copy attachment stream directly from the source.
    """
    codec_name = 'copy'
    encoder_options = {'map': int,
                       'source': str,
                       'filename': str,
                       'mimetype': str}

    optlist = []

    def parse_options(self, opt, stream=0):
        safe = self.safe_options(opt)

        stream = str(stream)
        optlist = []
        optlist.extend(['-c:t:' + stream, 'copy'])
        if 'filename' in safe:
            optlist.extend(['-metadata:s:t:' + stream, "filename=" + str(safe['filename'])])
        if 'mimetype' in safe:
            optlist.extend(['-metadata:s:t:' + stream, "mimetype=" + str(safe['mimetype'])])
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
    ffprobe_codec_name = "vorbis"
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
    ffprobe_codec_name = 'aac'
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
    ffprobe_codec_name = 'aac'

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
    ffprobe_codec_name = 'aac'

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
    ffprobe_codec_name = 'ac3'

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
    ffprobe_codec_name = 'eac3'

    def parse_options(self, opt, stream=0):
        if 'channels' in opt:
            c = opt['channels']
            if c > 8:
                opt['channels'] = 6
        if 'bitrate' in opt:
            br = opt['bitrate']
            if br > 640:
                opt['bitrate'] = 640
        return super(EAc3Codec, self).parse_options(opt, stream)


class TrueHDCodec(AudioCodec):
    """
    TrueHD audio codec.
    """
    codec_name = 'truehd'
    ffmpeg_codec_name = 'truehd'
    ffprobe_codec_name = 'truehd'
    truehd_experimental_enable = ['-strict', 'experimental']

    def parse_options(self, opt, stream=0):
        if 'channels' in opt:
            c = opt['channels']
            if c > 8:
                opt['channels'] = 8
        return super(TrueHDCodec, self).parse_options(opt, stream)

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        return self.truehd_experimental_enable


class FlacCodec(AudioCodec):
    """
    FLAC audio codec.
    """
    codec_name = 'flac'
    ffmpeg_codec_name = 'flac'
    ffprobe_codec_name = 'flac'
    flac_experimental_enable = ['-strict', 'experimental']

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        return self.flac_experimental_enable


class DtsCodec(AudioCodec):
    """
    DTS audio codec.
    """
    codec_name = 'dts'
    ffmpeg_codec_name = 'dts'
    ffprobe_codec_name = 'dts'
    dts_experimental_enable = ['-strict', 'experimental']

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        return self.dts_experimental_enable


class Mp3Codec(AudioCodec):
    """
    MP3 (MPEG layer 3) audio codec.
    """
    codec_name = 'mp3'
    ffmpeg_codec_name = 'libmp3lame'
    ffprobe_codec_name = 'mp3'


class Mp2Codec(AudioCodec):
    """
    MP2 (MPEG layer 2) audio codec.
    """
    codec_name = 'mp2'
    ffmpeg_codec_name = 'mp2'
    ffprobe_codec_name = 'mp2'


class OpusCodec(AudioCodec):
    """
    Opus audio codec
    """
    codec_name = 'opus'
    ffmpeg_codec_name = 'libopus'
    ffprobe_codec_name = 'opus'
    opus_experimental_enable = ['-strict', 'experimental']

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        return self.opus_experimental_enable


class PCMS24LECodec(AudioCodec):
    """
    PCM_S24LE Audio Codec
    """
    codec_name = 'pcm_s24le'
    ffmpeg_codec_name = 'pcm_s24le'
    ffprobe_codec_name = 'pcm_s24le'


class PCMS16LECodec(AudioCodec):
    """
    PCM_S16LE Audio Codec
    """
    codec_name = 'pcm_s16le'
    ffmpeg_codec_name = 'pcm_s16le'
    ffprobe_codec_name = 'pcm_s16le'


# Video Codecs
class TheoraCodec(VideoCodec):
    """
    Theora video codec.
    """
    codec_name = 'theora'
    ffmpeg_codec_name = 'libtheora'
    ffprobe_codec_name = 'theora'
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
    ffprobe_codec_name = 'h264'
    codec_params = 'x264-params'
    levels = [1, 1.1, 1.2, 1.3, 2, 2.1, 2.2, 3, 3.1, 3.2, 4, 4.1, 4.2, 5, 5.1, 5.2, 6, 6.1, 6.2]
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'preset': str,  # common presets are ultrafast, superfast, veryfast,
        # faster, fast, medium(default), slow, slower, veryslow
        'profile': str,  # default: not-set, for valid values see above link
        'level': float,  # default: not-set, values range from 3.0 to 4.2
        'tune': str,  # default: not-set, for valid values see above link
        'wscale': int,  # special handlers for the even number requirements of h264
        'hscale': int,  # special handlers for the even number requirements of h264
        'params': str  # x264-params
    })
    scale_filter = 'scale'

    @staticmethod
    def codec_specific_level_conversion(ffprobe_level):
        return ffprobe_level / 10.0

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
            if safe['level'] not in self.levels:
                try:
                    safe['level'] = [x for x in self.levels if x < safe['level']][-1]
                except:
                    del safe['level']

        if 'preset' in safe:
            optlist.extend(['-preset', safe['preset']])
        if 'profile' in safe:
            optlist.extend(['-profile:v', safe['profile']])
        if 'level' in safe:
            optlist.extend(['-level', '%0.1f' % safe['level']])
        if 'params' in safe:
            optlist.extend(['-%s' % self.codec_params, safe['params']])
        if 'tune' in safe:
            optlist.extend(['-tune', safe['tune']])
        if 'wscale' in safe and 'hscale' in safe:
            optlist.extend(['-vf', '%s=%s:%s' % (self.scale_filter, safe['wscale'], safe['hscale'])])
        elif 'wscale' in safe:
            optlist.extend(['-vf', '%s=%s:trunc(ow/a/2)*2' % (self.scale_filter, safe['wscale'])])
        elif 'hscale' in safe:
            optlist.extend(['-vf', '%s=trunc((oh*a)/2)*2:%s' % (self.scale_filter, safe['hscale'])])
        return optlist


class H264CodecAlt(H264Codec):
    """
    H.264/AVC video codec alternate.
    """
    codec_name = 'x264'


class NVEncH264Codec(H264Codec):
    """
    Nvidia H.264/AVC video codec.
    """
    codec_name = 'h264_nvenc'
    ffmpeg_codec_name = 'h264_nvenc'
    scale_filter = 'scale_npp'
    encoder_options = H264Codec.encoder_options.copy()
    encoder_options.update({
        'decode_device': str,
        'device': str,
    })

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = super(NVEncH264Codec, self)._codec_specific_produce_ffmpeg_list(safe, stream)
        if 'device' in safe:
            optlist.extend(['-filter_hw_device', safe['device']])
            if 'decode_device' in safe and safe['decode_device'] != safe['device']:
                optlist.extend(['-vf', 'hwdownload,format=nv12,hwupload'])
        elif 'decode_device' in safe:
            optlist.extend(['-vf', 'hwdownload,format=nv12,hwupload'])
        return optlist


class VideotoolboxEncH264(H264Codec):
    """
    Videotoolbox H.264/AVC video codec.
    """
    codec_name = 'h264_videotoolbox'
    ffmpeg_codec_name = 'h264_videotoolbox'


class OMXH264Codec(H264Codec):
    """
    OMX H.264/AVC video codec.
    """
    codec_name = 'h264_omx'
    ffmpeg_codec_name = 'h264_omx'


class H264VAAPICodec(H264Codec):
    """
    H.264/AVC VAAPI video codec.
    """
    codec_name = 'h264vaapi'
    ffmpeg_codec_name = 'h264_vaapi'
    scale_filter = 'scale_vaapi'
    default_fmt = 'nv12'
    encoder_options = H264Codec.encoder_options.copy()
    encoder_options.update({
        'decode_device': str,
        'device': str,
    })

    def _codec_specific_parse_options(self, safe, stream=0):
        if 'width' in safe and safe['width']:
            safe['width'] = 2 * round(safe['width'] / 2)
            safe['vaapi_wscale'] = safe['width']
            del(safe['width'])
        if 'height' in safe and safe['height']:
            if safe['height'] % 2 == 0:
                safe['vaapi_hscale'] = safe['height']
            del(safe['height'])
        if 'crf' in safe:
            safe['qp'] = safe['crf']
            del safe['crf']
            qp = safe['qp']
            if qp < 0 or qp > 52:
                del safe['qp']
            elif 'bitrate' in safe:
                del safe['bitrate']
        if 'pix_fmt' in safe:
            safe['vaapi_pix_fmt'] = safe['pix_fmt']
            del safe['pix_fmt']
        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = super(H264VAAPICodec, self)._codec_specific_produce_ffmpeg_list(safe, stream)
        if 'qp' in safe:
            optlist.extend(['-qp', str(safe['qp'])])
            if 'maxrate' in safe:
                optlist.extend(['-maxrate:v', str(safe['maxrate'])])
            if 'bufsize' in safe:
                optlist.extend(['-bufsize', str(safe['bufsize'])])

        if 'device' in safe:
            optlist.extend(['-filter_hw_device', safe['device']])
            if 'decode_device' in safe and safe['decode_device'] != safe['device']:
                optlist.extend(['-vf', 'hwdownload'])
        else:
            optlist.extend(['-vaapi_device', '/dev/dri/renderD128'])
            if 'decode_device' in safe:
                optlist.extend(['-vf', 'hwdownload'])

        fmt = safe['vaapi_pix_fmt'] if 'vaapi_pix_fmt' in safe else self.default_fmt
        fmtstr = ':format=%s' % safe['vaapi_pix_fmt'] if 'vaapi_pix_fmt' in safe else ""

        if 'vaapi_wscale' in safe and 'vaapi_hscale' in safe:
            optlist.extend(['-vf', 'format=%s|vaapi,hwupload,%s=w=%s:h=%s%s' % (fmt, self.scale_filter, safe['vaapi_wscale'], safe['vaapi_hscale'], fmtstr)])
        elif 'vaapi_wscale' in safe:
            optlist.extend(['-vf', 'format=%s|vaapi,hwupload,%s=w=%s:h=trunc(ow/a/2)*2%s' % (fmt, self.scale_filter, safe['vaapi_wscale'], fmtstr)])
        elif 'vaapi_hscale' in safe:
            optlist.extend(['-vf', 'format=%s|vaapi,hwupload,%s=w=trunc((oh*a)/2)*2:h=%s%s' % (fmt, self.scale_filter, safe['vaapi_hscale'], fmtstr)])
        else:
            fmtstr = ",%s=%s" % (self.scale_filter, fmtstr[1:]) if fmtstr else ""
            optlist.extend(['-vf', "format=%s|vaapi,hwupload%s" % (fmt, fmtstr)])
        return optlist


class H264QSVCodec(H264Codec):
    """
    H.264/AVC video codec.
    """
    codec_name = 'h264qsv'
    ffmpeg_codec_name = 'h264_qsv'
    scale_filter = 'scale_qsv'

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = []
        if 'level' in safe:
            if safe['level'] not in self.levels:
                try:
                    safe['level'] = [x for x in self.levels if x < safe['level']][-1]
                except:
                    del safe['level']

        if 'level' in safe:
            optlist.extend(['-level', '%0.0f' % (safe['level'] * 10)])
            del safe['level']

        optlist.extend(super(H264QSVCodec, self)._codec_specific_produce_ffmpeg_list(safe, stream))
        optlist.extend(['-look_ahead', '0'])
        return optlist


class H265Codec(VideoCodec):
    """
    H.265/AVC video codec.
    """
    codec_name = 'h265'
    ffmpeg_codec_name = 'libx265'
    ffprobe_codec_name = 'hevc'
    codec_params = 'x265-params'
    levels = [1, 2, 2.1, 3, 3.1, 4, 4.1, 5, 5.1, 5.2, 6, 6.1, 6.2]  # 8.5 excluded
    encoder_options = VideoCodec.encoder_options.copy()
    encoder_options.update({
        'preset': str,  # common presets are ultrafast, superfast, veryfast,
        # faster, fast, medium(default), slow, slower, veryslow
        'profile': str,  # default: not-set, for valid values see above link
        'level': float,  # default: not-set, values range from 3.0 to 4.2
        'tune': str,  # default: not-set, for valid values see above link
        'wscale': int,  # special handlers for the even number requirements of h265
        'hscale': int,  # special handlers for the even number requirements of h265
        'params': str,  # x265-params
        'framedata': dict  # dynamic params for framedata
    })
    scale_filter = 'scale'

    @staticmethod
    def codec_specific_level_conversion(ffprobe_level):
        return ffprobe_level / 30.0

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

    def safe_framedata(self, opts):
        params = ""
        if 'hdr' in opts and opts['hdr']:
            params += "hdr-opt=1:"
        if 'repeat-headers' in opts and opts['repeat-headers']:
            params += "repeat-headers=1:"
        if 'color_primaries' in opts:
            params += "colorprim=" + opts['color_primaries'] + ":"
        if 'color_transfer' in opts:
            params += "transfer=" + opts['color_transfer'] + ":"
        if 'color_space' in opts:
            params += "colormatrix=" + opts['color_space'] + ":"
        if 'side_data_list' in opts:
            for side_data in opts['side_data_list']:
                if side_data.get('side_data_type') == 'Mastering display metadata':
                    red_x = side_data['red_x']
                    red_y = side_data['red_y']
                    green_x = side_data['green_x']
                    green_y = side_data['green_y']
                    blue_x = side_data['blue_x']
                    blue_y = side_data['blue_y']
                    wp_x = side_data['white_point_x']
                    wp_y = side_data['white_point_y']
                    min_l = side_data['min_luminance']
                    max_l = side_data['max_luminance']
                    params += "master-display=G(%d,%d)B(%d,%d)R(%d,%d)WP(%d,%d)L(%d,%d):" % (green_x, green_y, blue_x, blue_y, red_x, red_y, wp_x, wp_y, max_l, min_l)
                elif side_data.get('side_data_type') == 'Content light level metadata':
                    max_content = side_data['max_content']
                    max_average = side_data['max_average']
                    params += "max-cll=%d,%d:" % (max_content, max_average)
        return params[:-1]

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = []

        if 'level' in safe:
            if safe['level'] not in self.levels:
                try:
                    safe['level'] = [x for x in self.levels if x < safe['level']][-1]
                except:
                    del safe['level']

        if 'preset' in safe:
            optlist.extend(['-preset', safe['preset']])
        if 'profile' in safe:
            optlist.extend(['-profile:v', safe['profile']])
        if 'level' in safe:
            optlist.extend(['-level', '%0.1f' % safe['level']])
        params = ""
        if 'params' in safe:
            params = safe['params']
        if 'framedata' in safe:
            if params:
                params = params + ":"
            params = params + self.safe_framedata(safe['framedata'])
        if params:
            optlist.extend(['-%s' % self.codec_params, params])
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


class H265CodecAlt(H265Codec):
    """
    H.265/AVC video codec alternate.
    """
    codec_name = 'hevc'


class H265QSVCodec(H265Codec):
    """
    HEVC video codec.
    """
    codec_name = 'h265qsv'
    ffmpeg_codec_name = 'hevc_qsv'
    scale_filter = 'scale_qsv'

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = []
        if 'level' in safe:
            if safe['level'] not in self.levels:
                try:
                    safe['level'] = [x for x in self.levels if x < safe['level']][-1]
                except:
                    del safe['level']

        if 'level' in safe:
            optlist.extend(['-level', '%0.0f' % (safe['level'] * 10)])
            del safe['level']

        optlist.extend(super(H265QSVCodec, self)._codec_specific_produce_ffmpeg_list(safe, stream))
        return optlist


class H265QSVCodecAlt(H265QSVCodec):
    """
    HEVC video codec alternate.
    """
    codec_name = 'hevcqsv'


class H265QSVCodecPatched(H265QSVCodec):
    """
    HEVC QSV alternate designed to work with patched FFMPEG that supports HDR metadata.
    Patch
        https://patchwork.ffmpeg.org/project/ffmpeg/patch/20201202131826.10558-1-omondifredrick@gmail.com/
    Github issue
        https://github.com/mdhiggins/sickbeard_mp4_automator/issues/1366
    """
    codec_name = 'hevcqsvpatched'
    codec_params = 'qsv_params'

    def safe_framedata(self, opts):
        params = ""
        if 'color_primaries' in opts:
            params += "colorprim=" + opts['color_primaries'] + ":"
        if 'color_transfer' in opts:
            params += "transfer=" + opts['color_transfer'] + ":"
        if 'color_space' in opts:
            params += "colormatrix=" + opts['color_space'] + ":"
        if 'side_data_list' in opts:
            for side_data in opts['side_data_list']:
                if side_data.get('side_data_type') == 'Mastering display metadata':
                    red_x = side_data['red_x']
                    red_y = side_data['red_y']
                    green_x = side_data['green_x']
                    green_y = side_data['green_y']
                    blue_x = side_data['blue_x']
                    blue_y = side_data['blue_y']
                    wp_x = side_data['white_point_x']
                    wp_y = side_data['white_point_y']
                    min_l = side_data['min_luminance']
                    min_l = 50 if min_l < 50 else min_l
                    max_l = side_data['max_luminance']
                    max_l = 10000000 if max_l > 10000000 else max_l
                    params += "master-display=G(%d,%d)B(%d,%d)R(%d,%d)WP(%d,%d)L(%d,%d):" % (green_x, green_y, blue_x, blue_y, red_x, red_y, wp_x, wp_y, min_l, max_l)
                elif side_data.get('side_data_type') == 'Content light level metadata':
                    max_content = side_data['max_content']
                    max_average = side_data['max_average']
                    if max_content == 0 and max_average == 0:
                        continue
                    max_content = 1000 if max_content > 1000 else max_content
                    max_average = 400 if max_average < 400 else max_average
                    max_content = max_average if max_content < max_average else max_content
                    params += "max-cll=%d,%d:" % (max_content, max_average)
        return params[:-1]


class H265VAAPICodec(H265Codec):
    """
    H.265/AVC VAAPI video codec.
    """
    codec_name = 'h265vaapi'
    ffmpeg_codec_name = 'hevc_vaapi'
    scale_filter = 'scale_vaapi'
    default_fmt = 'nv12'
    encoder_options = H265Codec.encoder_options.copy()
    encoder_options.update({
        'decode_device': str,
        'device': str,
    })

    def _codec_specific_parse_options(self, safe, stream=0):
        if 'width' in safe and safe['width']:
            safe['width'] = 2 * round(safe['width'] / 2)
            safe['vaapi_wscale'] = safe['width']
            del(safe['width'])
        if 'height' in safe and safe['height']:
            if safe['height'] % 2 == 0:
                safe['vaapi_hscale'] = safe['height']
            del(safe['height'])
        if 'crf' in safe:
            safe['qp'] = safe['crf']
            del safe['crf']
            qp = safe['qp']
            if qp < 0 or qp > 52:
                del safe['qp']
            elif 'bitrate' in safe:
                del safe['bitrate']
        if 'pix_fmt' in safe:
            safe['vaapi_pix_fmt'] = safe['pix_fmt']
            del safe['pix_fmt']
        return safe

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = super(H265VAAPICodec, self)._codec_specific_produce_ffmpeg_list(safe, stream)
        if 'qp' in safe:
            optlist.extend(['-qp', str(safe['qp'])])
            if 'maxrate' in safe:
                optlist.extend(['-maxrate:v', str(safe['maxrate'])])
            if 'bufsize' in safe:
                optlist.extend(['-bufsize', str(safe['bufsize'])])

        if 'device' in safe:
            optlist.extend(['-filter_hw_device', safe['device']])
            if 'decode_device' in safe and safe['decode_device'] != safe['device']:
                optlist.extend(['-vf', 'hwdownload'])
        else:
            optlist.extend(['-vaapi_device', '/dev/dri/renderD128'])
            if 'decode_device' in safe:
                optlist.extend(['-vf', 'hwdownload'])

        fmt = safe['vaapi_pix_fmt'] if 'vaapi_pix_fmt' in safe else self.default_fmt
        fmtstr = ':format=%s' % safe['vaapi_pix_fmt'] if 'vaapi_pix_fmt' in safe else ""

        if 'vaapi_wscale' in safe and 'vaapi_hscale' in safe:
            optlist.extend(['-vf', 'format=%s|vaapi,hwupload,%s=w=%s:h=%s%s' % (fmt, self.scale_filter, safe['vaapi_wscale'], safe['vaapi_hscale'], fmtstr)])
        elif 'vaapi_wscale' in safe:
            optlist.extend(['-vf', 'format=%s|vaapi,hwupload,%s=w=%s:h=trunc(ow/a/2)*2%s' % (fmt, self.scale_filter, safe['vaapi_wscale'], fmtstr)])
        elif 'vaapi_hscale' in safe:
            optlist.extend(['-vf', 'format=%s|vaapi,hwupload,%s=w=trunc((oh*a)/2)*2:h=%s%s' % (fmt, self.scale_filter, safe['vaapi_hscale'], fmtstr)])
        else:
            fmtstr = ",%s=%s" % (self.scale_filter, fmtstr[1:]) if fmtstr else ""
            optlist.extend(['-vf', "format=%s|vaapi,hwupload%s" % (fmt, fmtstr)])
        return optlist


class NVEncH265Codec(H265Codec):
    """
    Nvidia H.265/AVC video codec.
    """
    codec_name = 'h265_nvenc'
    ffmpeg_codec_name = 'hevc_nvenc'
    scale_filter = 'scale_npp'
    encoder_options = H265Codec.encoder_options.copy()
    encoder_options.update({
        'decode_device': str,
        'device': str,
    })

    def _codec_specific_produce_ffmpeg_list(self, safe, stream=0):
        optlist = super(NVEncH265Codec, self)._codec_specific_produce_ffmpeg_list(safe, stream)
        if 'device' in safe:
            optlist.extend(['-filter_hw_device', safe['device']])
            if 'decode_device' in safe and safe['decode_device'] != safe['device']:
                optlist.extend(['-vf', 'hwdownload,format=nv12,hwupload'])
        elif 'decode_device' in safe:
            optlist.extend(['-vf', 'hwdownload,format=nv12,hwupload'])
        return optlist


class NVEncH265CodecAlt(NVEncH265Codec):
    """
    Nvidia H.265/AVC video codec alternate.
    """
    codec_name = 'hevc_nvenc'


class VideotoolboxEncH265(H265Codec):
    """
    Videotoolbox H.265/HEVC video codec.
    """
    codec_name = 'h265_videotoolbox'
    ffmpeg_codec_name = 'hevc_videotoolbox'


class DivxCodec(VideoCodec):
    """
    DivX video codec.
    """
    codec_name = 'divx'
    ffmpeg_codec_name = 'mpeg4'
    ffprobe_codec_name = 'mpeg4'


class Vp8Codec(VideoCodec):
    """
    Google VP8 video codec.
    """
    codec_name = 'vp8'
    ffmpeg_codec_name = 'libvpx'
    ffprobe_codec_name = 'vp8'


class Vp9Codec(VideoCodec):
    """
    Google VP9 video codec.
    """
    codec_name = 'vp9'
    ffmpeg_codec_name = 'libvpx-vp9'
    ffprobe_codec_name = 'vp9'


class Vp9QSVCodec(Vp9Codec):
    """
    Google VP9 QSV video codec.
    """
    codec_name = 'vp9qsv'
    ffmpeg_codec_name = 'vp9_qsv'


class Vp9QSVAltCodec(Vp9QSVCodec):
    """
    Google VP9 QSV video codec alt.
    """
    codec_name = 'vp9_qsv'


class H263Codec(VideoCodec):
    """
    H.263 video codec.
    """
    codec_name = 'h263'
    ffmpeg_codec_name = 'h263'
    ffprobe_codec_name = 'h263'


class FlvCodec(VideoCodec):
    """
    Flash Video codec.
    """
    codec_name = 'flv'
    ffmpeg_codec_name = 'flv'
    ffprobe_codec_name = 'flv1'


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
    ffprobe_codec_name = 'mpeg1video'


class Mpeg2Codec(MpegCodec):
    """
    MPEG-2 video codec.
    """
    codec_name = 'mpeg2'
    ffmpeg_codec_name = 'mpeg2video'
    ffprobe_codec_name = 'mpeg2video'


# Subtitle Codecs
class MOVTextCodec(SubtitleCodec):
    """
    mov_text subtitle codec.
    """
    codec_name = 'mov_text'
    ffmpeg_codec_name = 'mov_text'
    ffprobe_codec_name = 'mov_text'


class SrtCodec(SubtitleCodec):
    """
    SRT subtitle codec.
    """
    codec_name = 'srt'
    ffmpeg_codec_name = 'srt'
    ffprobe_codec_name = 'srt'


class WebVTTCodec(SubtitleCodec):
    """
    SRT subtitle codec.
    """
    codec_name = 'webvtt'
    ffmpeg_codec_name = 'webvtt'
    ffprobe_codec_name = 'webvtt'


class PGSCodec(SubtitleCodec):
    """
    PGS subtitle codec.
    """
    codec_name = 'pgs'
    ffmpeg_codec_name = 'copy'  # Does not have an encoder
    ffprobe_codec_name = 'hdmv_pgs_subtitle'


class PGSCodecAlt(PGSCodec):
    """
    PGS subtitle codec alternate.
    """
    codec_name = 'hdmv_pgs_subtitle'


class SSACodec(SubtitleCodec):
    """
    SSA (SubStation Alpha) subtitle.
    """
    codec_name = 'ass'
    ffmpeg_codec_name = 'ass'
    ffprobe_codec_name = 'ass'


class SubRip(SubtitleCodec):
    """
    SubRip subtitle.
    """
    codec_name = 'subrip'
    ffmpeg_codec_name = 'subrip'
    ffprobe_codec_name = 'subrip'


class DVBSub(SubtitleCodec):
    """
    DVB subtitles.
    """
    codec_name = 'dvbsub'
    ffmpeg_codec_name = 'dvbsub'
    ffprobe_codec_name = 'dvb_subtitle'


class DVDSub(SubtitleCodec):
    """
    DVD subtitles.
    """
    codec_name = 'dvdsub'
    ffmpeg_codec_name = 'dvdsub'
    ffprobe_codec_name = 'dvd_subtitle'


class DVDSubAlt(DVDSub):
    """
    DVD subtitles alternate.
    """
    codec_name = 'dvd_subtitle'


audio_codec_list = [
    AudioNullCodec, AudioCopyCodec, VorbisCodec, AacCodec, Mp3Codec, Mp2Codec,
    FdkAacCodec, FAacCodec, EAc3Codec, Ac3Codec, DtsCodec, FlacCodec, OpusCodec, PCMS24LECodec, PCMS16LECodec,
    TrueHDCodec
]

video_codec_list = [
    VideoNullCodec, VideoCopyCodec,
    TheoraCodec,
    H263Codec,
    H264Codec, H264CodecAlt, H264QSVCodec, H264VAAPICodec, OMXH264Codec, VideotoolboxEncH264, NVEncH264Codec,
    H265Codec, H265QSVCodecAlt, H265QSVCodec, H265CodecAlt, H265QSVCodecPatched, H265VAAPICodec, VideotoolboxEncH265, NVEncH265Codec, NVEncH265CodecAlt,
    DivxCodec,
    Vp8Codec,
    Vp9Codec, Vp9QSVCodec, Vp9QSVAltCodec,
    FlvCodec,
    Mpeg1Codec,
    Mpeg2Codec
]

subtitle_codec_list = [
    SubtitleNullCodec, SubtitleCopyCodec, MOVTextCodec, SrtCodec, SSACodec, SubRip, DVDSub,
    DVBSub, DVDSubAlt, WebVTTCodec, PGSCodec, PGSCodecAlt
]

attachment_codec_list = [
    AttachmentCopyCodec
]
