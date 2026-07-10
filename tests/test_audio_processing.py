"""
Tests for audio compression and loudnorm processing in MediaProcessor.

Run with:  python3 -m pytest tests/ -v
       or: python3 -m unittest discover -s tests -v
"""

import sys
import os
import logging
import types
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub out optional third-party dependencies so the import chain succeeds
# without requiring the full production environment.
# ---------------------------------------------------------------------------
def _mock_package(name):
    """Insert a MagicMock for *name* and all dotted sub-names already known."""
    m = MagicMock()
    sys.modules.setdefault(name, m)
    return m

_plexapi = _mock_package('plexapi')
for _sub in ('myplex', 'server', 'library'):
    sys.modules.setdefault('plexapi.' + _sub, MagicMock())

for _mod in ('tmdbsimple', 'mutagen', 'mutagen.mp4', 'mutagen.id3',
             'requests', 'babelfish', 'guessit', 'subliminal'):
    _mock_package(_mod)

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from converter.ffmpeg import MediaStreamInfo, MediaInfo
from resources.mediaprocessor import MediaProcessor

# Suppress module-level logging during tests (warnings, info, debug all hidden)
logging.disable(logging.CRITICAL)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FAKE_COMPAND_FILTER = 'attacks=0:points=-80/-90|-45/-45|-27/-25|0/-7|20/-7'
FAKE_LOUDNORM_FILTER = (
    'loudnorm=I=-16.0:TP=-1.5:LRA=11.0'
    ':measured_I=-23.0:measured_TP=-3.0:measured_LRA=7.0'
    ':measured_thresh=-33.0:offset=-0.5:linear=true'
)
FAKE_LOUDNORM_VALUES = {
    'input_i': '-23.0',
    'input_tp': '-3.0',
    'input_lra': '7.0',
    'input_thresh': '-33.0',
    'target_offset': '-0.5',
}


# ---------------------------------------------------------------------------
# Stream / info builders
# ---------------------------------------------------------------------------

def make_video_stream(index=0, codec='h264', width=1920, height=1080,
                      pix_fmt='yuv420p', profile='High'):
    s = MediaStreamInfo()
    s.index = index
    s.type = 'video'
    s.codec = codec
    s.video_width = width
    s.video_height = height
    s.pix_fmt = pix_fmt
    s.profile = profile
    s.bitrate = 5_000_000
    s.fps = 24.0
    s.video_level = 4.0
    s.field_order = None
    s.framedata = {}
    s.metadata = {}
    s.disposition = {}
    s.color = {}
    return s


def make_audio_stream(index=1, codec='dts', channels=6, language='eng',
                      bitrate=None, profile=None, metadata=None, samplerate=48000):
    s = MediaStreamInfo()
    s.index = index
    s.type = 'audio'
    s.codec = codec
    s.audio_channels = channels
    s.audio_samplerate = samplerate
    s.bitrate = bitrate
    s.profile = profile
    s.metadata = {'language': language}
    if metadata:
        s.metadata.update(metadata)
    s.disposition = {}
    s.color = {}
    return s


def make_media_info(*streams):
    info = MediaInfo()
    for s in streams:
        info.streams.append(s)
    return info


# ---------------------------------------------------------------------------
# Settings builder
# ---------------------------------------------------------------------------

def make_settings(**overrides):
    """Return a SimpleNamespace with all settings required by generateOptions."""
    defaults = dict(
        # FFmpeg paths
        ffmpeg='/usr/bin/ffmpeg',
        ffprobe='/usr/bin/ffprobe',
        # Video
        vcodec=['h264'],
        hdr={
            'space': [], 'transfer': [], 'primaries': [],
            'codec': [], 'pix_fmt': [], 'profile': [],
            'filter': None, 'forcefilter': False,
            'preset': None, 'codec_params': None,
        },
        vbitrateratio={},
        vmaxbitrate=0,
        vwidth=0,
        video_level=0.0,
        vcrf=-1,
        vcrf_profiles=[],
        vfilter=None,
        vforcefilter=False,
        vprofile=[],
        preset=None,
        codec_params=None,
        dynamic_params=False,
        pix_fmt=[],
        keep_source_pix_fmt=True,
        removebvs=False,
        keep_titles=False,
        sanitize_disposition=[],
        # Audio
        acodec=['ac3'],
        awl=[],
        adl='',
        audio_original_language=False,
        abitrate=128,
        avbr=0,
        amaxbitrate=0,
        maxchannels=0,
        aprofile='',
        afilter=None,
        aforcefilter=False,
        audio_samplerates=[],
        audio_sampleformat='',
        audio_atmos_force_copy=False,
        audio_copyoriginal=False,
        audio_first_language_stream=False,
        aac_adtstoasc=False,
        ignored_audio_dispositions=[],
        force_audio_defaults=False,
        unique_audio_dispositions=False,
        stream_codec_combinations=[],
        audio_sorting=[],
        audio_sorting_default=[],
        audio_sorting_codecs=[],
        afilterchannels={},
        # Compression / loudnorm (off by default)
        acompression=False,
        acompression_filter=FAKE_COMPAND_FILTER,
        loudnorm=False,
        loudnorm_i=-16.0,
        loudnorm_tp=-1.5,
        loudnorm_lra=11.0,
        loudnorm_linear=True,
        # Universal audio
        ua=['aac'],
        ua_bitrate=128,
        ua_vbr=0,
        ua_first_only=False,
        ua_profile='',
        ua_filter=None,
        ua_forcefilter=False,
        # Subtitles (minimal — no subtitle streams in tests)
        scodec=[],
        scodec_image=[],
        swl=[],
        sdl='',
        subtitle_original_language=False,
        sub_first_language_stream=False,
        embedsubs=False,
        embedimgsubs=False,
        embedonlyinternalsubs=True,
        ignore_embedded_subs=True,
        ignored_sub_dispositions=[],
        unique_sub_dispositions=False,
        force_subtitle_defaults=False,
        sub_sorting=[],
        sub_sorting_codecs=[],
        burn_subtitles=False,
        # Misc
        attachmentcodec=[],
        subencoding=None,
        threads=0,
        output_format='mp4',
        preopts=[],
        postopts=[],
        hwdevices={},
        strip_metadata=False,
        tagfile=False,
        downloadsubs=False,
        downloadforcedsubs=False,
        includehi=False,
        sub_providers=[],
    )
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Helper to build a MediaProcessor with a fully mocked Converter
# ---------------------------------------------------------------------------

def make_processor(settings):
    """
    Create a MediaProcessor with a mocked Converter (no real ffmpeg required).
    Returns (processor, MockConverter class).
    """
    codecs_dict = {
        'aac': {'encoders': ['aac'], 'decoders': ['aac']},
        'ac3': {'encoders': ['ac3'], 'decoders': ['ac3']},
        'dts': {'encoders': [], 'decoders': ['dca']},
        'h264': {'encoders': ['libx264'], 'decoders': ['h264']},
        'eac3': {'encoders': ['eac3'], 'decoders': ['eac3']},
    }

    with patch('resources.mediaprocessor.Converter') as MockConverter:
        instance = MagicMock()
        MockConverter.return_value = instance
        instance.ffmpeg.codecs = codecs_dict
        instance.ffmpeg.pix_fmts = {}
        instance.codec_name_to_ffmpeg_codec_name.return_value = None
        MockConverter.codec_name_to_ffprobe_codec_name.return_value = None
        MockConverter.codec_name_to_ffmpeg_codec_name.return_value = None
        MockConverter.encoder.return_value = None

        mp = MediaProcessor(settings, logging.getLogger('test'))

    # Re-attach the mock converter so methods that call self.converter work
    mp.converter = instance
    return mp, MockConverter


# ---------------------------------------------------------------------------
# Tests: isAudioCompressedProcessed
# ---------------------------------------------------------------------------

class TestIsAudioCompressedProcessed(unittest.TestCase):

    def setUp(self):
        self.mp, _ = make_processor(make_settings())

    def _stream(self, metadata=None, profile=None):
        s = make_audio_stream(profile=profile)
        if metadata:
            s.metadata.update(metadata)
        return s

    def test_compand_tag_detected(self):
        s = self._stream(metadata={'compand': '1'})
        self.assertTrue(self.mp.isAudioCompressedProcessed(s))

    def test_comp_in_title_detected(self):
        s = self._stream(metadata={'title': 'Stereo (Compressed & Normalized)'})
        self.assertTrue(self.mp.isAudioCompressedProcessed(s))

    def test_partial_word_with_comp(self):
        s = self._stream(metadata={'title': 'Dolby Atmos Compatibility'})
        self.assertTrue(self.mp.isAudioCompressedProcessed(s))

    def test_clean_stream_not_detected(self):
        s = self._stream()
        self.assertFalse(self.mp.isAudioCompressedProcessed(s))

    def test_loudnorm_tag_alone_not_compressed(self):
        s = self._stream(metadata={'loudnorm': '1'})
        self.assertFalse(self.mp.isAudioCompressedProcessed(s))

    def test_none_metadata_handled(self):
        s = make_audio_stream()
        s.metadata = None
        self.assertFalse(self.mp.isAudioCompressedProcessed(s))


# ---------------------------------------------------------------------------
# Tests: isAudioLoudnormProcessed
# ---------------------------------------------------------------------------

class TestIsAudioLoudnormProcessed(unittest.TestCase):

    def setUp(self):
        self.mp, _ = make_processor(make_settings())

    def _stream(self, metadata=None):
        s = make_audio_stream()
        if metadata:
            s.metadata.update(metadata)
        return s

    def test_loudnorm_tag_detected(self):
        s = self._stream(metadata={'loudnorm': '1'})
        self.assertTrue(self.mp.isAudioLoudnormProcessed(s))

    def test_dynaudnorm_tag_detected(self):
        s = self._stream(metadata={'dynaudnorm': '1'})
        self.assertTrue(self.mp.isAudioLoudnormProcessed(s))

    def test_norm_in_title_detected(self):
        s = self._stream(metadata={'title': 'Stereo Normalized'})
        self.assertTrue(self.mp.isAudioLoudnormProcessed(s))

    def test_clean_stream_not_detected(self):
        s = self._stream()
        self.assertFalse(self.mp.isAudioLoudnormProcessed(s))

    def test_compand_tag_alone_not_loudnorm(self):
        s = self._stream(metadata={'compand': '1'})
        self.assertFalse(self.mp.isAudioLoudnormProcessed(s))

    def test_none_metadata_handled(self):
        s = make_audio_stream()
        s.metadata = None
        self.assertFalse(self.mp.isAudioLoudnormProcessed(s))


# ---------------------------------------------------------------------------
# Tests: isAudioStreamAtmos
# ---------------------------------------------------------------------------

class TestIsAudioStreamAtmos(unittest.TestCase):

    def setUp(self):
        self.mp, _ = make_processor(make_settings())

    def test_atmos_in_profile(self):
        s = make_audio_stream(profile='Dolby Atmos')
        self.assertTrue(self.mp.isAudioStreamAtmos(s))

    def test_atmos_case_insensitive(self):
        s = make_audio_stream(profile='ATMOS 7.1')
        self.assertTrue(self.mp.isAudioStreamAtmos(s))

    def test_non_atmos_profile(self):
        s = make_audio_stream(profile='DTS-HD MA')
        self.assertFalse(self.mp.isAudioStreamAtmos(s))

    def test_no_profile(self):
        s = make_audio_stream(profile=None)
        self.assertFalse(self.mp.isAudioStreamAtmos(s))


# ---------------------------------------------------------------------------
# Tests: getLoudNormFilter
# ---------------------------------------------------------------------------

class TestGetLoudNormFilter(unittest.TestCase):

    def setUp(self):
        settings = make_settings(loudnorm_i=-16.0, loudnorm_tp=-1.5,
                                 loudnorm_lra=11.0, loudnorm_linear=True)
        self.mp, _ = make_processor(settings)

    def test_linear_uses_measured_values(self):
        with patch.object(self.mp, 'getLoudNormValues', return_value=FAKE_LOUDNORM_VALUES):
            result = self.mp.getLoudNormFilter('/tmp/test.mkv', 0)
        self.assertIn('measured_I=-23.0', result)
        self.assertIn('linear=true', result)
        self.assertIn('I=-16.0', result)

    def test_linear_fallback_to_single_pass_when_values_none(self):
        with patch.object(self.mp, 'getLoudNormValues', return_value=None):
            result = self.mp.getLoudNormFilter('/tmp/test.mkv', 0)
        self.assertIn('linear=false', result)

    def test_single_pass_when_linear_disabled(self):
        self.mp.settings.loudnorm_linear = False
        with patch.object(self.mp, 'getLoudNormValues') as mock_values:
            result = self.mp.getLoudNormFilter('/tmp/test.mkv', 0)
        mock_values.assert_not_called()
        self.assertIn('linear=false', result)

    def test_pre_filter_forwarded_to_getLoudNormValues(self):
        pre = FAKE_COMPAND_FILTER
        with patch.object(self.mp, 'getLoudNormValues', return_value=None) as mock_values:
            self.mp.getLoudNormFilter('/tmp/test.mkv', 0, pre_filter=pre)
        mock_values.assert_called_once_with('/tmp/test.mkv', 0, pre_filter=pre)

    def test_no_pre_filter_forwarded_as_none(self):
        with patch.object(self.mp, 'getLoudNormValues', return_value=None) as mock_values:
            self.mp.getLoudNormFilter('/tmp/test.mkv', 0)
        mock_values.assert_called_once_with('/tmp/test.mkv', 0, pre_filter=None)


# ---------------------------------------------------------------------------
# Integration tests: generateOptions audio output
# ---------------------------------------------------------------------------

class TestGenerateOptionsAudio(unittest.TestCase):
    """
    Call generateOptions() with a real MediaInfo object (fake streams) and a
    mocked Converter so no FFmpeg binary is needed.  getLoudNormFilter is also
    patched to return a deterministic filter string.
    """

    def _run(self, settings, audio_stream, extra_streams=None):
        """
        Build a MediaInfo with one video + one audio stream, call
        generateOptions, and return the audio_settings list.
        """
        mp, _ = make_processor(settings)

        video = make_video_stream()
        streams = [video, audio_stream] + (extra_streams or [])
        info = make_media_info(*streams)

        with patch.object(mp, 'getLoudNormFilter', return_value=FAKE_LOUDNORM_FILTER):
            options, _, _, _, _ = mp.generateOptions('/tmp/test.mkv', info=info)

        return options['audio']

    # ------------------------------------------------------------------
    # Surround → stereo UA with compression + loudnorm
    # ------------------------------------------------------------------

    def test_surround_ua_has_aac_codec(self):
        """UA track from a 5.1 source must use the UA codec (aac)."""
        settings = make_settings(ua=['aac'], acompression=True, loudnorm=True)
        audio = make_audio_stream(codec='dts', channels=6)
        result = self._run(settings, audio)
        ua_tracks = [a for a in result if 'universal-audio' in a.get('debug', '')]
        self.assertEqual(len(ua_tracks), 1)
        self.assertEqual(ua_tracks[0]['codec'], 'aac')

    def test_surround_ua_has_stereo_channels(self):
        settings = make_settings(ua=['aac'], acompression=True, loudnorm=True)
        audio = make_audio_stream(codec='dts', channels=6)
        result = self._run(settings, audio)
        ua_tracks = [a for a in result if 'universal-audio' in a.get('debug', '')]
        self.assertEqual(ua_tracks[0]['channels'], 2)

    def test_surround_ua_filter_contains_compand(self):
        """UA filter chain must include the compand filter when compression=True."""
        settings = make_settings(ua=['aac'], acompression=True, loudnorm=False)
        audio = make_audio_stream(codec='dts', channels=6)
        result = self._run(settings, audio)
        ua_tracks = [a for a in result if 'universal-audio' in a.get('debug', '')]
        self.assertIn(FAKE_COMPAND_FILTER, ua_tracks[0].get('filter', ''))

    def test_surround_ua_filter_contains_loudnorm(self):
        """UA filter chain must include the loudnorm filter when loudnorm=True."""
        settings = make_settings(ua=['aac'], acompression=False, loudnorm=True)
        audio = make_audio_stream(codec='dts', channels=6)
        result = self._run(settings, audio)
        ua_tracks = [a for a in result if 'universal-audio' in a.get('debug', '')]
        self.assertIn(FAKE_LOUDNORM_FILTER, ua_tracks[0].get('filter', ''))

    def test_surround_ua_compand_before_loudnorm_in_filter(self):
        """Compand must precede loudnorm in the filter chain."""
        settings = make_settings(ua=['aac'], acompression=True, loudnorm=True)
        audio = make_audio_stream(codec='dts', channels=6)
        result = self._run(settings, audio)
        ua_tracks = [a for a in result if 'universal-audio' in a.get('debug', '')]
        f = ua_tracks[0].get('filter', '')
        compand_pos = f.find(FAKE_COMPAND_FILTER)
        loudnorm_pos = f.find(FAKE_LOUDNORM_FILTER)
        self.assertGreater(compand_pos, -1, "compand not in filter")
        self.assertGreater(loudnorm_pos, -1, "loudnorm not in filter")
        self.assertLess(compand_pos, loudnorm_pos,
                        "compand must appear before loudnorm")

    def test_surround_ua_metadata_compand_tag(self):
        """UA track must carry COMPAND=1 metadata tag when compression applied."""
        settings = make_settings(ua=['aac'], acompression=True, loudnorm=False)
        audio = make_audio_stream(codec='dts', channels=6)
        result = self._run(settings, audio)
        ua_tracks = [a for a in result if 'universal-audio' in a.get('debug', '')]
        self.assertEqual(ua_tracks[0].get('metadata', {}).get('COMPAND'), '1')

    def test_surround_ua_metadata_loudnorm_tag(self):
        """UA track must carry LOUDNORM=1 metadata tag when loudnorm applied."""
        settings = make_settings(ua=['aac'], acompression=False, loudnorm=True)
        audio = make_audio_stream(codec='dts', channels=6)
        result = self._run(settings, audio)
        ua_tracks = [a for a in result if 'universal-audio' in a.get('debug', '')]
        self.assertEqual(ua_tracks[0].get('metadata', {}).get('LOUDNORM'), '1')

    def test_surround_ua_both_metadata_tags_present(self):
        """UA track carries both COMPAND=1 and LOUDNORM=1 when both are enabled."""
        settings = make_settings(ua=['aac'], acompression=True, loudnorm=True)
        audio = make_audio_stream(codec='dts', channels=6)
        result = self._run(settings, audio)
        ua_tracks = [a for a in result if 'universal-audio' in a.get('debug', '')]
        meta = ua_tracks[0].get('metadata', {})
        self.assertEqual(meta.get('COMPAND'), '1')
        self.assertEqual(meta.get('LOUDNORM'), '1')

    # ------------------------------------------------------------------
    # Main (non-UA) track metadata
    # ------------------------------------------------------------------

    def test_main_track_compand_tag(self):
        """Main surround track also gets COMPAND=1 when compression enabled."""
        settings = make_settings(acodec=['ac3'], ua=['aac'],
                                 acompression=True, loudnorm=False)
        audio = make_audio_stream(codec='dts', channels=6)
        result = self._run(settings, audio)
        main_tracks = [a for a in result if 'universal-audio' not in a.get('debug', '')]
        self.assertEqual(main_tracks[0].get('metadata', {}).get('COMPAND'), '1')

    def test_main_track_loudnorm_tag(self):
        """Main track gets LOUDNORM=1 when loudnorm enabled."""
        settings = make_settings(acodec=['ac3'], ua=['aac'],
                                 acompression=False, loudnorm=True)
        audio = make_audio_stream(codec='dts', channels=6)
        result = self._run(settings, audio)
        main_tracks = [a for a in result if 'universal-audio' not in a.get('debug', '')]
        self.assertEqual(main_tracks[0].get('metadata', {}).get('LOUDNORM'), '1')

    # ------------------------------------------------------------------
    # No double-compression
    # ------------------------------------------------------------------

    def test_already_compressed_stream_skips_compression(self):
        """Stream with compand metadata must not have compand added to its filter."""
        settings = make_settings(acompression=True, loudnorm=False, ua=['aac'])
        audio = make_audio_stream(codec='dts', channels=6,
                                  metadata={'compand': '1'})
        result = self._run(settings, audio)
        main_tracks = [a for a in result if 'universal-audio' not in a.get('debug', '')]
        self.assertNotIn(FAKE_COMPAND_FILTER,
                         main_tracks[0].get('filter') or '')

    def test_already_compressed_stream_still_gets_loudnorm(self):
        """Loudnorm must run even when compression is skipped."""
        settings = make_settings(acompression=True, loudnorm=True, ua=['aac'])
        audio = make_audio_stream(codec='dts', channels=6,
                                  metadata={'compand': '1'})
        result = self._run(settings, audio)
        main_tracks = [a for a in result if 'universal-audio' not in a.get('debug', '')]
        self.assertIn(FAKE_LOUDNORM_FILTER,
                      main_tracks[0].get('filter', ''))

    def test_already_compressed_stream_preserves_compand_tag(self):
        """COMPAND=1 must be written explicitly so the tag survives re-encoding."""
        settings = make_settings(acompression=True, loudnorm=False, ua=['aac'])
        audio = make_audio_stream(codec='dts', channels=6,
                                  metadata={'compand': '1'})
        result = self._run(settings, audio)
        main_tracks = [a for a in result if 'universal-audio' not in a.get('debug', '')]
        self.assertEqual(main_tracks[0].get('metadata', {}).get('COMPAND'), '1')

    # ------------------------------------------------------------------
    # Normalization always runs (idempotent)
    # ------------------------------------------------------------------

    def test_already_normalized_stream_still_gets_loudnorm(self):
        """Loudnorm applies even when the stream already has a loudnorm tag."""
        settings = make_settings(acompression=False, loudnorm=True, ua=['aac'])
        audio = make_audio_stream(codec='dts', channels=6,
                                  metadata={'loudnorm': '1'})
        result = self._run(settings, audio)
        main_tracks = [a for a in result if 'universal-audio' not in a.get('debug', '')]
        self.assertIn(FAKE_LOUDNORM_FILTER,
                      main_tracks[0].get('filter', ''))

    # ------------------------------------------------------------------
    # Atmos exclusion
    # ------------------------------------------------------------------

    def test_atmos_stream_skips_compression(self):
        """Atmos stream must not have the compand filter applied."""
        settings = make_settings(audio_atmos_force_copy=True,
                                 acompression=True, loudnorm=False,
                                 ua=['aac'])
        audio = make_audio_stream(codec='eac3', channels=8,
                                  profile='Dolby Atmos')
        result = self._run(settings, audio)
        main_tracks = [a for a in result if 'universal-audio' not in a.get('debug', '')]
        self.assertNotIn(FAKE_COMPAND_FILTER,
                         main_tracks[0].get('filter') or '')

    def test_atmos_stream_skips_loudnorm(self):
        """Atmos stream must not have the loudnorm filter applied."""
        settings = make_settings(audio_atmos_force_copy=True,
                                 acompression=False, loudnorm=True,
                                 ua=['aac'])
        audio = make_audio_stream(codec='eac3', channels=8,
                                  profile='Dolby Atmos')
        result = self._run(settings, audio)
        main_tracks = [a for a in result if 'universal-audio' not in a.get('debug', '')]
        self.assertNotIn(FAKE_LOUDNORM_FILTER,
                         main_tracks[0].get('filter') or '')

    def test_atmos_stream_is_forced_copy(self):
        """Atmos streams must be codec=copy when audio_atmos_force_copy=True."""
        settings = make_settings(audio_atmos_force_copy=True,
                                 acompression=True, loudnorm=True,
                                 ua=['aac'])
        audio = make_audio_stream(codec='eac3', channels=8,
                                  profile='Dolby Atmos')
        result = self._run(settings, audio)
        main_tracks = [a for a in result if 'universal-audio' not in a.get('debug', '')]
        self.assertEqual(main_tracks[0]['codec'], 'copy')

    # ------------------------------------------------------------------
    # Disabled compression / loudnorm produce no tags
    # ------------------------------------------------------------------

    def test_no_tags_when_both_disabled(self):
        settings = make_settings(acompression=False, loudnorm=False, ua=['aac'])
        audio = make_audio_stream(codec='dts', channels=6)
        result = self._run(settings, audio)
        main_tracks = [a for a in result if 'universal-audio' not in a.get('debug', '')]
        self.assertIsNone(main_tracks[0].get('metadata'))

    def test_no_ua_compand_tag_when_compression_disabled(self):
        settings = make_settings(acompression=False, loudnorm=False, ua=['aac'])
        audio = make_audio_stream(codec='dts', channels=6)
        result = self._run(settings, audio)
        ua_tracks = [a for a in result if 'universal-audio' in a.get('debug', '')]
        self.assertIsNone(ua_tracks[0].get('metadata'))

    # ------------------------------------------------------------------
    # UA double-compression guard
    # ------------------------------------------------------------------

    def test_ua_skips_compand_filter_when_source_already_compressed(self):
        """UA must not apply compand when source stream is already compressed."""
        settings = make_settings(ua=['aac'], acompression=True, loudnorm=False)
        audio = make_audio_stream(codec='dts', channels=6,
                                  metadata={'compand': '1'})
        result = self._run(settings, audio)
        ua_tracks = [a for a in result if 'universal-audio' in a.get('debug', '')]
        self.assertNotIn(FAKE_COMPAND_FILTER,
                         ua_tracks[0].get('filter') or '')

    def test_ua_preserves_compand_tag_when_source_already_compressed(self):
        """UA must still carry COMPAND=1 when compression is skipped for already-compressed source."""
        settings = make_settings(ua=['aac'], acompression=True, loudnorm=False)
        audio = make_audio_stream(codec='dts', channels=6,
                                  metadata={'compand': '1'})
        result = self._run(settings, audio)
        ua_tracks = [a for a in result if 'universal-audio' in a.get('debug', '')]
        self.assertEqual(ua_tracks[0].get('metadata', {}).get('COMPAND'), '1')

    def test_ua_still_applies_loudnorm_when_source_already_compressed(self):
        """UA loudnorm must run even when UA compression is skipped."""
        settings = make_settings(ua=['aac'], acompression=True, loudnorm=True)
        audio = make_audio_stream(codec='dts', channels=6,
                                  metadata={'compand': '1'})
        result = self._run(settings, audio)
        ua_tracks = [a for a in result if 'universal-audio' in a.get('debug', '')]
        self.assertIn(FAKE_LOUDNORM_FILTER,
                      ua_tracks[0].get('filter', ''))


if __name__ == '__main__':
    unittest.main(verbosity=2)
