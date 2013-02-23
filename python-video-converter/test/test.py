#!/usr/bin/env python

# modify the path so that parent directory is in it
import sys
sys.path.append('../')

import unittest
import os
import os.path
import datetime

from converter import ffmpeg, formats, avcodecs, Converter, ConverterError


class TestFFMpeg(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def assertRaisesSpecific(self, exception, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
            raise Exception('Expected exception %s not raised' % repr(exception))
        except exception, ex:
            return ex

    @staticmethod
    def ensure_notexist(f):
        if os.path.exists(f):
            os.unlink(f)

    def test_ffmpeg_probe(self):
        self.assertRaisesSpecific(ffmpeg.FFMpegError, ffmpeg.FFMpeg,
            ffmpeg_path='/foo', ffprobe_path='/bar')

        f = ffmpeg.FFMpeg()

        self.assertEqual(None, f.probe('/nonexistent'))
        self.assertEqual(None, f.probe('/dev/null'))

        info = f.probe('test1.ogg')
        self.assertEqual('ogg', info.format.format)
        self.assertAlmostEqual(33.00, info.format.duration, places=2)
        self.assertEqual(2, len(info.streams))

        v = info.streams[0]
        self.assertEqual(v, info.video)
        self.assertEqual('video', v.type)
        self.assertEqual('theora', v.codec)
        self.assertEqual(720, v.video_width)
        self.assertEqual(400, v.video_height)
        self.assertAlmostEqual(25.00, v.video_fps, places=2)

        a = info.streams[1]
        self.assertEqual(a, info.audio)
        self.assertEqual('audio', a.type)
        self.assertEqual('vorbis', a.codec)
        self.assertEqual(2, a.audio_channels)
        self.assertEqual(48000, a.audio_samplerate)

        self.assertEqual(repr(info),
            'MediaInfo(format=MediaFormatInfo(format=ogg, duration=33.00), streams=[MediaStreamInfo(type=video, codec=theora, width=720, height=400, fps=25.0), MediaStreamInfo(type=audio, codec=vorbis, channels=2, rate=48000)])')

    def test_ffmpeg_convert(self):
        f = ffmpeg.FFMpeg()

        def consume(fn, *args, **kwargs):
            return list(fn(*args, **kwargs))

        self.assertRaisesSpecific(ffmpeg.FFMpegError, consume,
            f.convert, '/nonexistent', '/tmp/output.ogg', [])

        self.assertRaisesSpecific(ffmpeg.FFMpegConvertError, consume,
            f.convert, '/etc/passwd', '/tmp/output.ogg', [])

        info = f.probe('test1.ogg')

        conv = f.convert('test1.ogg', '/tmp/output.ogg', [
            '-acodec', 'libvorbis', '-ab', '16k', '-ac', '1', '-ar', '11025',
            '-vcodec', 'libtheora', '-r', '15', '-s', '360x200', '-b', '128k'
        ])

        last_tc = 0.0
        for tc in conv:
            assert (tc > last_tc and tc <= info.format.duration + 0.1), (last_tc, tc, info.format.duration)


        info = f.probe('/tmp/output.ogg')
        self.assertEqual('ogg', info.format.format)
        self.assertAlmostEqual(33.00, info.format.duration, places=0)
        self.assertEqual(2, len(info.streams))

        self.assertEqual('video', info.video.type)
        self.assertEqual('theora', info.video.codec)
        self.assertEqual(360, info.video.video_width)
        self.assertEqual(200, info.video.video_height)
        self.assertAlmostEqual(15.00, info.video.video_fps, places=2)

        self.assertEqual('audio', info.audio.type)
        self.assertEqual('vorbis', info.audio.codec)
        self.assertEqual(1, info.audio.audio_channels)
        self.assertEqual(11025, info.audio.audio_samplerate)

    def test_ffmpeg_thumbnail(self):
        f = ffmpeg.FFMpeg()
        thumb = '/tmp/shot.png'

        self.assertRaisesSpecific(IOError, f.thumbnail, '/nonexistent', 10, thumb)

        self.ensure_notexist(thumb)
        f.thumbnail('test1.ogg', 10, thumb)
        self.assertTrue(os.path.exists(thumb))

        self.ensure_notexist(thumb)
        self.assertRaisesSpecific(ffmpeg.FFMpegError, f.thumbnail, 'test1.ogg', 34, thumb)
        self.assertFalse(os.path.exists(thumb))

    def test_formats(self):
        c = formats.BaseFormat()
        self.assertRaisesSpecific(ValueError, c.parse_options, {})
        self.assertEqual(['-f', 'ogg'], formats.OggFormat().parse_options({'format': 'ogg'}))

    def test_avcodecs(self):
        c = avcodecs.BaseCodec()
        self.assertRaisesSpecific(ValueError, c.parse_options, {})

        c.encoder_options = { 'foo': int, 'bar': bool }
        self.assertEqual({}, c.safe_options({ 'baz': 1, 'quux': 1, 'foo': 'w00t'}))
        self.assertEqual({'foo':42,'bar':False}, c.safe_options({'foo':'42','bar':0}))

        c = avcodecs.AudioCodec()
        c.codec_name = 'doctest'
        c.ffmpeg_codec_name = 'doctest'

        self.assertEqual(['-acodec', 'doctest'],
            c.parse_options({'codec': 'doctest', 'channels': 0, 'bitrate': 0, 'samplerate': 0}))

        self.assertEqual(['-acodec', 'doctest', '-ac', '1', '-ab', '64k', '-ar', '44100'],
            c.parse_options({'codec': 'doctest', 'channels': '1', 'bitrate': '64', 'samplerate': '44100'}))

        c = avcodecs.VideoCodec()
        c.codec_name = 'doctest'
        c.ffmpeg_codec_name = 'doctest'

        self.assertEqual(['-vcodec', 'doctest'],
            c.parse_options({'codec': 'doctest', 'fps': 0, 'bitrate': 0, 'width': 0, 'height': '480' }))

        self.assertEqual(['-vcodec', 'doctest', '-r', '25', '-b', '300k', '-s', '320x240', '-aspect', '320:240'],
            c.parse_options({'codec': 'doctest', 'fps': '25', 'bitrate': '300', 'width': 320, 'height': 240 }))

        self.assertEqual(['-vcodec', 'doctest', '-s', '384x240', '-aspect', '384:240', '-vf', 'crop=32:0:320:240'],
            c.parse_options({'codec': 'doctest', 'src_width': 640, 'src_height': 400, 'mode': 'crop',
                'width': 320, 'height': 240 }))

        self.assertEqual(['-vcodec', 'doctest', '-s', '320x240', '-aspect', '320:240', '-vf', 'crop=0:20:320:200'],
            c.parse_options({'codec': 'doctest', 'src_width': 640, 'src_height': 480, 'mode': 'crop',
                'width': 320, 'height': 200 }))

        self.assertEqual(['-vcodec', 'doctest', '-s', '320x200', '-aspect', '320:200', '-vf', 'pad=320:240:0:20'],
            c.parse_options({'codec': 'doctest', 'src_width': 640, 'src_height': 400, 'mode': 'pad',
                'width': 320, 'height': 240 }))

        self.assertEqual(['-vcodec', 'doctest', '-s', '266x200', '-aspect', '266:200', '-vf', 'pad=320:200:27:0'],
            c.parse_options({'codec': 'doctest', 'src_width': 640, 'src_height': 480, 'mode': 'pad',
                'width': 320, 'height': 200 }))

        self.assertEqual(['-vcodec', 'doctest', '-s', '320x240', '-aspect', '320:240'],
            c.parse_options({'codec': 'doctest', 'src_width': 640, 'src_height': 480, 'width': 320 }))

        self.assertEqual(['-vcodec', 'doctest', '-s', '320x240', '-aspect', '320:240'],
            c.parse_options({'codec': 'doctest', 'src_width': 640, 'src_height': 480, 'height': 240 }))

    def test_converter(self):

        c = Converter()

        def verify_progress(p):
            if not p:
                return False

            li = list(p)
            if len(li) < 1:
                return False

            prev = 0
            for i in li:
                if type(i) != int or i < 0 or i > 100:
                    return False
                if i < prev:
                    return False
                prev = i
            return True

        self.assertRaisesSpecific(ConverterError, c.parse_options, None)
        self.assertRaisesSpecific(ConverterError, c.parse_options, {})
        self.assertRaisesSpecific(ConverterError, c.parse_options, {'format': 'foo'})

        self.assertRaisesSpecific(ConverterError, c.parse_options, {'format': 'ogg'})
        self.assertRaisesSpecific(ConverterError, c.parse_options, {'format': 'ogg', 'video': 'whatever'})
        self.assertRaisesSpecific(ConverterError, c.parse_options, {'format': 'ogg', 'audio': {}})
        self.assertRaisesSpecific(ConverterError, c.parse_options,
            {'format': 'ogg', 'audio': {'codec': 'bogus'}})

        self.assertEqual(['-an', '-vcodec', 'libtheora', '-r', '25', '-f', 'ogg'],
            c.parse_options({'format':'ogg','video':{'codec':'theora','fps':25}}))
        self.assertEqual(['-acodec', 'copy', '-vcodec', 'copy', '-f', 'ogg'],
            c.parse_options({'format':'ogg','audio':{'codec':'copy'},'video':{'codec':'copy'}}))

        info = c.probe('test1.ogg')
        self.assertEqual('theora', info.video.codec)
        self.assertEqual(720, info.video.video_width)
        self.assertEqual(400, info.video.video_height)

        f = '/tmp/shot.png'

        self.ensure_notexist(f)
        c.thumbnail('test1.ogg', 10, f)
        self.assertTrue(os.path.exists(f))
        os.unlink(f)

        conv = c.convert('test1.ogg', '/tmp/output.ogg', {
            'format': 'ogg',
            'video': {
                'codec': 'theora', 'width': 160, 'height': 120, 'fps': 15, 'bitrate': 300 },
            'audio': {
                'codec': 'vorbis', 'channels': 1, 'bitrate': 32 }
            })

        self.assertTrue(verify_progress(conv))


if __name__ == '__main__':
    unittest.main()
