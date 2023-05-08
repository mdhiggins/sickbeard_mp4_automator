import os
import sys
import locale

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser as ConfigParser
try:
    from importlib import reload
except ImportError:
    pass
import logging
from resources.extensions import *


class SMAConfigParser(ConfigParser, object):
    def getlist(self, section, option, vars=None, separator=",", default=[], lower=True, replace=[' ']):
        value = self.get(section, option, vars=vars)

        if not isinstance(value, str) and isinstance(value, list):
            return value

        if value == '':
            return list(default)

        value = value.split(separator)

        for r in replace:
            value = [x.replace(r, '') for x in value]
        if lower:
            value = [x.lower() for x in value]

        value = [x.strip() for x in value]
        return value

    def getdict(self, section, option, vars=None, listseparator=",", dictseparator=":", default={}, lower=True, replace=[' '], valueModifier=None):
        l = self.getlist(section, option, vars, listseparator, [], lower, replace)
        output = dict(default)
        for listitem in l:
            split = listitem.split(dictseparator, 1)
            if len(split) > 1:
                if valueModifier:
                    try:
                        split[1] = valueModifier(split[1])
                    except:
                        self.log.exception("Invalid value for getdict")
                        continue
                output[split[0]] = split[1]
        return output

    def getpath(self, section, option, vars=None):
        path = self.get(section, option, vars=vars).strip()
        if path == '':
            return None
        return os.path.normpath(path)

    def getdirectory(self, section, option, vars=None):
        directory = self.getpath(section, option, vars)
        try:
            os.makedirs(directory)
        except:
            pass
        return directory

    def getdirectories(self, section, option, vars=None, separator=",", default=[]):
        directories = self.getlist(section, option, vars=vars, separator=separator, default=default, lower=False)
        directories = [os.path.normpath(x) for x in directories]
        for d in directories:
            if not os.path.isdir(d):
                try:
                    os.makedirs(d)
                except:
                    pass
        return directories

    def getextension(self, section, option, vars=None):
        extension = self.get(section, option, vars=vars).lower().replace(' ', '').replace('.', '')
        if extension == '':
            return None
        return extension

    def getextensions(self, section, option, separator=",", vars=None):
        return self.getlist(section, option, vars, separator, replace=[' ', '.'])

    def getint(self, section, option, vars=None, fallback=0):
        if sys.version[0] == '2':
            return int(super(SMAConfigParser, self).get(section, option, vars=vars, fallback=fallback))
        return super(SMAConfigParser, self).getint(section, option, vars=vars, fallback=fallback)

    def getboolean(self, section, option, vars=None, fallback=False):
        return super(SMAConfigParser, self).getboolean(section, option, vars=vars, fallback=fallback)


class ReadSettings:
    DEFAULTS = {
        'Converter': {
            'ffmpeg': 'ffmpeg' if os.name != 'nt' else 'ffmpeg.exe',
            'ffprobe': 'ffprobe' if os.name != 'nt' else 'ffprobe.exe',
            'threads': 0,
            'hwaccels': '',
            'hwaccel-decoders': '',
            'hwdevices': '',
            'hwaccel-output-format': '',
            'output-directory': '',
            'output-directory-space-ratio': 0.0,
            'output-format': 'mp4',
            'output-extension': 'mp4',
            'temp-extension': '',
            'minimum-size': '0',
            'ignored-extensions': 'nfo, ds_store',
            'copy-to': '',
            'move-to': '',
            'delete-original': True,
            'process-same-extensions': False,
            'bypass-if-copying-all': False,
            'force-convert': False,
            'post-process': False,
            'wait-post-process': False,
            'detailed-progress': False,
            'opts-separator': ',',
            'preopts': '',
            'postopts': '',
            'regex-directory-replace': r'[^\w\-_\. ]',
        },
        'Permissions': {
            'chmod': '0644',
            'uid': -1,
            'gid': -1,
        },
        'Metadata': {
            'relocate-moov': True,
            'full-path-guess': True,
            'tag': True,
            'tag-language': 'eng',
            'download-artwork': 'poster',
            'sanitize-disposition': '',
            'strip-metadata': False,
            'keep-titles': False,
        },
        'Video': {
            'codec': 'h264, x264',
            'max-bitrate': 0,
            'bitrate-ratio': '',
            'crf': -1,
            'crf-profiles': '',
            'preset': '',
            'codec-parameters': '',
            'dynamic-parameters': False,
            'max-width': 0,
            'profile': '',
            'max-level': 0.0,
            'pix-fmt': '',
            'prioritize-source-pix-fmt': True,
            'filter': '',
            'force-filter': False,
        },
        'HDR': {
            'codec': '',
            'pix-fmt': '',
            'space': 'bt2020nc',
            'transfer': 'smpte2084',
            'primaries': 'bt2020',
            'preset': '',
            'codec-parameters': '',
            'filter': '',
            'force-filter': False,
            'profile': '',
        },
        'Audio': {
            'codec': 'ac3',
            'languages': '',
            'default-language': '',
            'include-original-language': True,
            'first-stream-of-language': False,
            'channel-bitrate': 128,
            'variable-bitrate': 0,
            'max-bitrate': 0,
            'max-channels': 0,
            'filter': '',
            'profile': '',
            'force-filter': False,
            'sample-rates': '',
            'sample-format': '',
            'copy-original': False,
            'aac-adtstoasc': False,
            'ignored-dispositions': '',
            'force-default': False,
            'unique-dispositions': False,
            'stream-codec-combinations': '',
        },
        'Audio.Sorting': {
            'sorting': 'language, channels.d, map, d.comment',
            'default-sorting': 'channels.d, map, d.comment',
            'codecs': '',
        },
        'Universal Audio': {
            'codec': 'aac',
            'channel-bitrate': 128,
            'variable-bitrate': 0,
            'first-stream-only': False,
            'filter': '',
            'profile': '',
            'force-filter': False,
        },
        'Audio.ChannelFilters': {
            '6-2': 'pan=stereo|FL=0.5*FC+0.707*FL+0.707*BL+0.5*LFE|FR=0.5*FC+0.707*FR+0.707*BR+0.5*LFE',
        },
        'Subtitle': {
            'codec': 'mov_text',
            'codec-image-based': '',
            'languages': '',
            'default-language': '',
            'include-original-language': False,
            'first-stream-of-language': False,
            'encoding': '',
            'burn-subtitles': False,
            'burn-dispositions': '',
            'embed-subs': True,
            'embed-image-subs': False,
            'embed-only-internal-subs': False,
            'filename-dispositions': 'forced',
            'ignore-embedded-subs': False,
            'ignored-dispositions': '',
            'force-default': False,
            'unique-dispositions': False,
            'attachment-codec': '',
            'remove-bitstream-subs': False,
        },
        'Subtitle.Sorting': {
            'sorting': 'language, d.comment, d.default.d, d.forced.d',
            'codecs': '',
            'burn-sorting': 'language, d.comment, d.default.d, d.forced.d',
        },
        'Subtitle.CleanIt': {
            'enabled': False,
            'config-path': '',
            'tags': '',
        },
        'Subtitle.FFSubsync': {
            'enabled': False,
        },
        'Subtitle.Subliminal': {
            'download-subs': False,
            'download-forced-subs': False,
            'include-hearing-impaired-subs': False,
            'providers': '',
        },
        'Subtitle.Subliminal.Auth': {
            'opensubtitles': '',
            'tvsubtitles': '',
        },
        'Sonarr': {
            'host': 'localhost',
            'port': 8989,
            'apikey': '',
            'ssl': False,
            'webroot': '',
            'force-rename': False,
            'rescan': True,
            'in-progress-check': True,
            'block-reprocess': False,
        },
        'Radarr': {
            'host': 'localhost',
            'port': 7878,
            'apikey': '',
            'ssl': False,
            'webroot': '',
            'force-rename': False,
            'rescan': True,
            'in-progress-check': True,
            'block-reprocess': False,
        },
        'Sickbeard': {
            'host': 'localhost',
            'port': 8081,
            'ssl': False,
            'apikey': '',
            'webroot': '',
            'username': '',
            'password': '',
        },
        'Sickrage': {
            'host': 'localhost',
            'port': 8081,
            'ssl': False,
            'apikey': '',
            'webroot': '',
            'username': '',
            'password': '',
        },
        'SABNZBD': {
            'convert': True,
            'sickbeard-category': 'sickbeard',
            'sickrage-category': 'sickrage',
            'sonarr-category': 'sonarr',
            'radarr-category': 'radarr',
            'bypass-category': 'bypass',
            'output-directory': '',
            'path-mapping': '',
        },
        'Deluge': {
            'sickbeard-label': 'sickbeard',
            'sickrage-label': 'sickrage',
            'sonarr-label': 'sonarr',
            'radarr-label': 'radarr',
            'bypass-label': 'bypass',
            'convert': True,
            'host': 'localhost',
            'port': 58846,
            'username': '',
            'password': '',
            'output-directory': '',
            'remove': False,
            'path-mapping': '',
        },
        'qBittorrent': {
            'sickbeard-label': 'sickbeard',
            'sickrage-label': 'sickrage',
            'sonarr-label': 'sonarr',
            'radarr-label': 'radarr',
            'bypass-label': 'bypass',
            'convert': True,
            'action-before': '',
            'action-after': '',
            'host': 'localhost',
            'port': 8080,
            'ssl': False,
            'username': '',
            'password': '',
            'output-directory': '',
            'path-mapping': '',
        },
        'uTorrent': {
            'sickbeard-label': 'sickbeard',
            'sickrage-label': 'sickrage',
            'sonarr-label': 'sonarr',
            'radarr-label': 'radarr',
            'bypass-label': 'bypass',
            'convert': True,
            'webui': False,
            'action-before': '',
            'action-after': '',
            'host': 'localhost',
            'ssl': False,
            'port': 8080,
            'username': '',
            'password': '',
            'output-directory': '',
            'path-mapping': '',
        },
        'Plex': {
            'username': '',
            'password': '',
            'servername': '',
            'host': 'localhost',
            'port': 32400,
            'refresh': False,
            'token': '',
            'ssl': True,
            'ignore-certs': False,
            'path-mapping': ''
        },
    }

    CONFIG_DEFAULT = "autoProcess.ini"
    CONFIG_DIRECTORY = "./config"
    RESOURCE_DIRECTORY = "./resources"
    RELATIVE_TO_ROOT = "../"
    ENV_CONFIG_VAR = "SMA_CONFIG"
    DYNAMIC_SECTIONS = ["Audio.ChannelFilters", "Subtitle.Subliminal.Auth"]

    @property
    def CONFIG_RELATIVEPATH(self):
        return os.path.join(self.CONFIG_DIRECTORY, self.CONFIG_DEFAULT)

    def __init__(self, configFile=None, logger=None):
        self.log = logger or logging.getLogger(__name__)

        self.log.info(sys.executable)
        if sys.version_info.major == 2:
            self.log.warning("Python 2 is no longer officially supported. Use with caution.")

        rootpath = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), self.RELATIVE_TO_ROOT))

        defaultConfigFile = os.path.normpath(os.path.join(rootpath, self.CONFIG_RELATIVEPATH))
        oldConfigFile = os.path.normpath(os.path.join(rootpath, self.CONFIG_DEFAULT))
        envConfigFile = os.environ.get(self.ENV_CONFIG_VAR)

        if envConfigFile and os.path.exists(os.path.realpath(envConfigFile)):
            configFile = os.path.realpath(envConfigFile)
            self.log.debug("%s environment variable override found." % (self.ENV_CONFIG_VAR))
        elif not configFile:
            if not os.path.exists(defaultConfigFile) and os.path.exists(oldConfigFile):
                try:
                    os.rename(oldConfigFile, defaultConfigFile)
                    self.log.info("Moved configuration file to new default location %s." % defaultConfigFile)
                    configFile = defaultConfigFile
                except:
                    configFile = oldConfigFile
                    self.log.debug("Unable to move configuration file to new location, using old location.")
            else:
                configFile = defaultConfigFile
            self.log.debug("Loading default config file.")

        if os.path.isdir(configFile):
            new = os.path.realpath(os.path.join(configFile, self.CONFIG_RELATIVEPATH))
            old = os.path.realpath(os.path.join(configFile, self.CONFIG_DEFAULT))
            if not os.path.exists(new) and os.path.exists(old):
                configFile = old
            else:
                configFile = new
            self.log.debug("Configuration file specified is a directory, joining with %s." % (self.CONFIG_DEFAULT))

        self.log.info("Loading config file %s." % configFile)

        # Setup encoding to avoid UTF-8 errors
        if sys.version[0] == '2':
            SYS_ENCODING = None
            try:
                locale.setlocale(locale.LC_ALL, "")
                SYS_ENCODING = locale.getpreferredencoding()
            except (locale.Error, IOError):
                pass

            # For OSes that are poorly configured just force UTF-8
            if not SYS_ENCODING or SYS_ENCODING in ('ANSI_X3.4-1968', 'US-ASCII', 'ASCII'):
                SYS_ENCODING = 'UTF-8'

            if not hasattr(sys, "setdefaultencoding"):
                reload(sys)

            try:
                # pylint: disable=E1101
                # On non-unicode builds this will raise an AttributeError, if encoding type is not valid it throws a LookupError
                sys.setdefaultencoding(SYS_ENCODING)
            except:
                self.log.exception("Sorry, your environment is not setup correctly for utf-8 support. Please fix your setup and try again")
                sys.exit("Sorry, your environment is not setup correctly for utf-8 support. Please fix your setup and try again")

        write = False  # Will be changed to true if a value is missing from the config file and needs to be written

        config = SMAConfigParser()
        if os.path.isfile(configFile):
            try:
                config.read(configFile)
            except:
                self.log.exception("Error reading config file %s." % configFile)
                sys.exit(1)
        else:
            self.log.error("Config file not found, creating %s." % configFile)
            # config.filename = filename
            write = True

        # Make sure all sections and all keys for each section are present
        for s in self.DEFAULTS:
            if not config.has_section(s):
                config.add_section(s)
                write = True
            if s in self.DYNAMIC_SECTIONS:
                continue
            for k in self.DEFAULTS[s]:
                if not config.has_option(s, k):
                    config.set(s, k, str(self.DEFAULTS[s][k]))
                    write = True

        # If any keys are missing from the config file, write them
        if write:
            self.writeConfig(config, configFile)

        config = self.migrateFromOld(config, configFile)

        self.readConfig(config)

        self._cofig = config
        self._configFile = configFile

    def readConfig(self, config):
        # Main converter settings
        section = "Converter"
        self.ffmpeg = config.getpath(section, 'ffmpeg', vars=os.environ)
        self.ffprobe = config.getpath(section, 'ffprobe', vars=os.environ)
        self.threads = config.getint(section, 'threads')
        self.hwaccels = config.getlist(section, 'hwaccels')
        self.hwaccel_decoders = config.getlist(section, "hwaccel-decoders")
        self.hwdevices = config.getdict(section, "hwdevices", lower=False, replace=[])
        self.hwoutputfmt = config.getdict(section, "hwaccel-output-format")
        self.output_dir = config.getdirectory(section, "output-directory")
        self.output_dir_ratio = config.getfloat(section, "output-directory-space-ratio")
        self.output_format = config.get(section, "output-format")
        self.output_extension = config.getextension(section, "output-extension")
        self.temp_extension = config.getextension(section, "temp-extension")
        self.minimum_size = config.getint(section, "minimum-size")
        self.ignored_extensions = config.getextensions(section, 'ignored-extensions')
        self.copyto = config.getdirectories(section, "copy-to", separator='|')
        self.moveto = config.getdirectory(section, "move-to")
        self.delete = config.getboolean(section, "delete-original")
        self.process_same_extensions = config.getboolean(section, "process-same-extensions")
        self.bypass_copy_all = config.getboolean(section, "bypass-if-copying-all")
        self.force_convert = config.getboolean(section, "force-convert")
        self.postprocess = config.getboolean(section, 'post-process')
        self.waitpostprocess = config.getboolean(section, 'wait-post-process')
        self.detailedprogress = config.getboolean(section, 'detailed-progress')
        self.opts_sep = config.get(section, "opts-separator")
        self.preopts = config.getlist(section, "preopts", separator=self.opts_sep)
        self.postopts = config.getlist(section, "postopts", separator=self.opts_sep)
        self.regex = config.get(section, 'regex-directory-replace', raw=True)

        if self.force_convert:
            self.process_same_extensions = True
            self.log.warning("Force-convert is true, so process-same-extensions is being overridden to true as well")

        # Permissions
        section = "Permissions"
        self.permissions = {}
        self.permissions['chmod'] = config.get(section, 'chmod')
        try:
            self.permissions['chmod'] = int(self.permissions['chmod'], 8)
        except:
            self.log.exception("Invalid permissions, defaulting to 644.")
            self.permissions['chmod'] = int("0644", 8)
        self.permissions['uid'] = config.getint(section, 'uid', vars=os.environ)
        self.permissions['gid'] = config.getint(section, 'gid', vars=os.environ)

        # Metadata
        section = "Metadata"
        self.relocate_moov = config.getboolean(section, "relocate-moov")
        self.fullpathguess = config.getboolean(section, "full-path-guess")
        self.tagfile = config.getboolean(section, "tag")
        self.taglanguage = config.get(section, "tag-language").lower()
        artwork = config.get(section, "download-artwork").lower()
        if artwork == "poster":
            self.artwork = True
            self.thumbnail = False
        elif 'thumb' in artwork:
            self.artwork = True
            self.thumbnail = True
        else:
            self.thumbnail = False
            try:
                self.artwork = config.getboolean(section, "download-artwork")
            except:
                self.artwork = True
                self.log.error("Invalid download-artwork value, defaulting to 'poster'.")
        self.sanitize_disposition = config.getlist(section, "sanitize-disposition")
        self.strip_metadata = config.getboolean(section, "strip-metadata")
        self.keep_titles = config.getboolean(section, "keep-titles")

        # Video
        section = "Video"
        self.vcodec = config.getlist(section, "codec")
        self.vmaxbitrate = config.getint(section, "max-bitrate")
        self.vbitrateratio = config.getdict(section, "bitrate-ratio", lower=True, valueModifier=float)
        self.vcrf = config.getint(section, "crf")

        self.vcrf_profiles = []
        vcrf_profiles = config.getlist(section, "crf-profiles")
        for vcrfp_raw in vcrf_profiles:
            vcrfp = vcrfp_raw.split(":")
            if len(vcrfp) == 4:
                try:
                    p = {
                        'source_bitrate': int(vcrfp[0]),
                        'crf': int(vcrfp[1]),
                        'maxrate': vcrfp[2],
                        'bufsize': vcrfp[3]
                    }
                    self.vcrf_profiles.append(p)
                except:
                    self.log.exception("Error parsing video-crf-profile '%s'." % vcrfp_raw)
            else:
                self.log.error("Invalid video-crf-profile length '%s'." % vcrfp_raw)
        self.vcrf_profiles.sort(key=lambda x: x['source_bitrate'], reverse=True)
        self.preset = config.get(section, 'preset')
        self.codec_params = config.get(section, 'codec-parameters')
        self.dynamic_params = config.getboolean(section, 'dynamic-parameters')
        self.vfilter = config.get(section, 'filter')
        self.vforcefilter = config.getboolean(section, 'force-filter')
        self.vwidth = config.getint(section, "max-width")
        self.video_level = config.getfloat(section, "max-level")
        self.vprofile = config.getlist(section, "profile")
        self.pix_fmt = config.getlist(section, "pix-fmt")
        self.keep_source_pix_fmt = config.getboolean(section, "prioritize-source-pix-fmt")

        # HDR
        section = "HDR"
        self.hdr = {}
        self.hdr['codec'] = config.getlist(section, 'codec')
        self.hdr['pix_fmt'] = config.getlist(section, "pix-fmt")
        self.hdr['space'] = config.getlist(section, 'space')
        self.hdr['transfer'] = config.getlist(section, 'transfer')
        self.hdr['primaries'] = config.getlist(section, 'primaries')
        self.hdr['preset'] = config.get(section, 'preset')
        self.hdr['codec_params'] = config.get(section, 'codec-parameters')
        self.hdr['filter'] = config.get(section, 'filter')
        self.hdr['forcefilter'] = config.getboolean(section, 'force-filter')
        self.hdr['profile'] = config.getlist(section, "profile")

        # Audio
        section = "Audio"
        self.acodec = config.getlist(section, "codec")
        self.awl = config.getlist(section, 'languages')
        self.adl = config.get(section, 'default-language').lower()
        self.audio_original_language = config.getboolean(section, 'include-original-language')
        self.abitrate = config.getint(section, "channel-bitrate")
        self.avbr = config.getint(section, "variable-bitrate")
        self.amaxbitrate = config.getint(section, 'max-bitrate')
        self.maxchannels = config.getint(section, 'max-channels')
        self.aprofile = config.get(section, "profile").lower()
        self.afilter = config.get(section, "filter")
        self.aforcefilter = config.getboolean(section, 'force-filter')
        self.audio_samplerates = [int(x) for x in config.getlist(section, "sample-rates") if x.isdigit()]
        self.audio_sampleformat = config.get(section, 'sample-format')
        self.audio_copyoriginal = config.getboolean(section, "copy-original")
        self.audio_first_language_stream = config.getboolean(section, "first-stream-of-language")
        self.aac_adtstoasc = config.getboolean(section, 'aac-adtstoasc')
        self.ignored_audio_dispositions = config.getlist(section, "ignored-dispositions")
        self.force_audio_defaults = config.getboolean(section, "force-default")
        self.unique_audio_dispositions = config.getboolean(section, "unique-dispositions")
        self.stream_codec_combinations = sorted([x.split(":") for x in config.getlist(section, "stream-codec-combinations")], key=lambda x: len(x), reverse=True)

        section = "Audio.Sorting"
        self.audio_sorting = config.getlist(section, 'sorting')
        self.audio_sorting_default = config.getlist(section, 'default-sorting')
        self.audio_sorting_codecs = config.getlist(section, 'codecs')

        section = "Audio.ChannelFilters"
        self.afilterchannels = {}
        if config.has_section(section):
            for key, value in config.items(section):
                if value:
                    try:
                        channels = [int(x) for x in key.split("-", 1)]
                        self.afilterchannels[channels[0]] = {channels[1]: config.get(section, key)}
                    except:
                        self.log.exception("Unable to parse %s %s, skipping." % (section, key))
                        continue

        # Universal Audio
        section = "Universal Audio"
        self.ua = config.getlist(section, "codec")
        self.ua_bitrate = config.getint(section, "channel-bitrate")
        self.ua_vbr = config.getint(section, "variable-bitrate")
        self.ua_first_only = config.getboolean(section, "first-stream-only")
        self.ua_profile = config.get(section, "profile").lower()
        self.ua_filter = config.get(section, "filter")
        self.ua_forcefilter = config.getboolean(section, 'force-filter')

        # Subtitles
        section = "Subtitle"
        self.scodec = config.getlist(section, 'codec')
        self.scodec_image = config.getlist(section, 'codec-image-based')
        self.swl = config.getlist(section, 'languages')
        self.sdl = config.get(section, 'default-language').lower()
        self.subtitle_original_language = config.getboolean(section, 'include-original-language')
        self.sub_first_language_stream = config.getboolean(section, "first-stream-of-language")
        self.subencoding = config.get(section, 'encoding')
        self.burn_subtitles = config.getboolean(section, "burn-subtitles")
        self.burn_dispositions = config.getlist(section, "burn-dispositions")
        self.embedsubs = config.getboolean(section, 'embed-subs')
        self.embedimgsubs = config.getboolean(section, 'embed-image-subs')
        self.embedonlyinternalsubs = config.getboolean(section, 'embed-only-internal-subs')
        self.filename_dispositions = config.getlist(section, "filename-dispositions")
        self.ignore_embedded_subs = config.getboolean(section, 'ignore-embedded-subs')
        self.ignored_subtitle_dispositions = config.getlist(section, "ignored-dispositions")
        self.force_subtitle_defaults = config.getboolean(section, "force-default")
        self.unique_subtitle_dispositions = config.getboolean(section, "unique-dispositions")
        self.attachmentcodec = config.getlist(section, 'attachment-codec')
        self.removebvs = config.getlist(section, 'remove-bitstream-subs')

        section = "Subtitle.Sorting"
        self.sub_sorting = config.getlist(section, 'sorting')
        self.sub_sorting_codecs = config.getlist(section, 'codecs')
        self.burn_sorting = config.getlist(section, 'burn-sorting')

        # CleanIt
        section = "Subtitle.CleanIt"
        self.cleanit = config.getboolean(section, "enabled")
        self.cleanit_config = config.get(section, "config-path")
        self.cleanit_tags = config.getlist(section, "tags")

        # FFSubsync
        section = "Subtitle.FFSubsync"
        self.ffsubsync = config.getboolean(section, "enabled")

        # Subliminal
        section = "Subtitle.Subliminal"
        self.downloadsubs = config.getboolean(section, "download-subs")
        self.downloadforcedsubs = config.getboolean(section, "download-forced-subs")
        self.hearing_impaired = config.getboolean(section, "include-hearing-impaired-subs")
        self.subproviders = config.getlist(section, 'providers')

        # Subliminal Auth Information
        section = "Subtitle.Subliminal.Auth"
        self.subproviders_auth = {}
        if config.has_section(section):
            for key, value in config.items(section):
                if value:
                    try:
                        rawcredentials = config.get(section, key)
                        credentials = [x.strip() for x in rawcredentials.split(":", 1)]
                        if len(credentials) < 2:
                            if rawcredentials:
                                self.log.error("Unable to parse %s %s, skipping." % (section, key))
                            continue
                        self.subproviders_auth[key.strip()] = {'username': credentials[0], 'password': credentials[1]}
                    except:
                        self.log.exception("Unable to parse %s %s, skipping." % (section, key))
                        continue

        # Sonarr
        section = "Sonarr"
        self.Sonarr = {}
        self.Sonarr['host'] = config.get(section, "host")
        self.Sonarr['port'] = config.getint(section, "port")
        self.Sonarr['apikey'] = config.get(section, "apikey")
        self.Sonarr['ssl'] = config.getboolean(section, "ssl")
        self.Sonarr['webroot'] = config.get(section, "webroot")
        if not self.Sonarr['webroot'].startswith("/"):
            self.Sonarr['webroot'] = "/" + self.Sonarr['webroot']
        if self.Sonarr['webroot'].endswith("/"):
            self.Sonarr['webroot'] = self.Sonarr['webroot'][:-1]
        self.Sonarr['rename'] = config.getboolean(section, "force-rename")
        self.Sonarr['rescan'] = config.getboolean(section, "rescan")
        self.Sonarr['in-progress-check'] = config.getboolean(section, "in-progress-check")
        self.Sonarr['blockreprocess'] = config.getboolean(section, "block-reprocess")

        # Radarr
        section = "Radarr"
        self.Radarr = {}
        self.Radarr['host'] = config.get(section, "host")
        self.Radarr['port'] = config.getint(section, "port")
        self.Radarr['apikey'] = config.get(section, "apikey")
        self.Radarr['ssl'] = config.getboolean(section, "ssl")
        self.Radarr['webroot'] = config.get(section, "webroot")
        if not self.Radarr['webroot'].startswith("/"):
            self.Radarr['webroot'] = "/" + self.Radarr['webroot']
        if self.Radarr['webroot'].endswith("/"):
            self.Radarr['webroot'] = self.Radarr['webroot'][:-1]
        self.Radarr['rename'] = config.getboolean(section, "force-rename")
        self.Radarr['rescan'] = config.getboolean(section, "rescan")
        self.Radarr['in-progress-check'] = config.getboolean(section, "in-progress-check")
        self.Radarr['blockreprocess'] = config.getboolean(section, "block-reprocess")

        # Sickbeard
        section = "Sickbeard"
        self.Sickbeard = {}
        self.Sickbeard['host'] = config.get(section, "host")
        self.Sickbeard['port'] = config.getint(section, "port")
        self.Sickbeard['apikey'] = config.get(section, "apikey")
        self.Sickbeard['webroot'] = config.get(section, "webroot")
        self.Sickbeard['ssl'] = config.getboolean(section, "ssl")
        self.Sickbeard['user'] = config.get(section, "username")
        self.Sickbeard['pass'] = config.get(section, "password")

        # Sickrage
        section = "Sickrage"
        self.Sickrage = {}
        self.Sickrage['host'] = config.get(section, "host")
        self.Sickrage['port'] = config.getint(section, "port")
        self.Sickrage['apikey'] = config.get(section, "apikey")
        self.Sickrage['webroot'] = config.get(section, "webroot")
        self.Sickrage['ssl'] = config.getboolean(section, "ssl")
        self.Sickrage['user'] = config.get(section, "username")
        self.Sickrage['pass'] = config.get(section, "password")

        # SAB
        section = "SABNZBD"
        self.SAB = {}
        self.SAB['convert'] = config.getboolean(section, "convert")
        self.SAB['sb'] = config.get(section, "Sickbeard-category").lower()
        self.SAB['sr'] = config.get(section, "Sickrage-category").lower()
        self.SAB['sonarr'] = config.get(section, "Sonarr-category").lower()
        self.SAB['radarr'] = config.get(section, "Radarr-category").lower()
        self.SAB['bypass'] = config.get(section, "Bypass-category").lower()
        self.SAB['output-dir'] = config.getdirectory(section, "output-directory")
        self.SAB['path-mapping'] = config.getdict(section, "path-mapping", dictseparator="=", lower=False, replace=[])

        # Deluge
        section = "Deluge"
        self.deluge = {}
        self.deluge['sb'] = config.get(section, "sickbeard-label").lower()
        self.deluge['sr'] = config.get(section, "sickrage-label").lower()
        self.deluge['sonarr'] = config.get(section, "sonarr-label").lower()
        self.deluge['radarr'] = config.get(section, "radarr-label").lower()
        self.deluge['bypass'] = config.get(section, "bypass-label").lower()
        self.deluge['convert'] = config.getboolean(section, "convert")
        self.deluge['host'] = config.get(section, "host")
        self.deluge['port'] = config.getint(section, "port")
        self.deluge['user'] = config.get(section, "username")
        self.deluge['pass'] = config.get(section, "password")
        self.deluge['output-dir'] = config.getdirectory(section, "output-directory")
        self.deluge['remove'] = config.getboolean(section, "remove")
        self.deluge['path-mapping'] = config.getdict(section, "path-mapping", dictseparator="=", lower=False, replace=[])

        # qBittorrent
        section = "qBittorrent"
        self.qBittorrent = {}
        self.qBittorrent['sb'] = config.get(section, "sickbeard-label").lower()
        self.qBittorrent['sr'] = config.get(section, "sickrage-label").lower()
        self.qBittorrent['sonarr'] = config.get(section, "sonarr-label").lower()
        self.qBittorrent['radarr'] = config.get(section, "radarr-label").lower()
        self.qBittorrent['bypass'] = config.get(section, "bypass-label").lower()
        self.qBittorrent['convert'] = config.getboolean(section, "convert")
        self.qBittorrent['output-dir'] = config.getdirectory(section, "output-directory")
        self.qBittorrent['actionbefore'] = config.get(section, "action-before")
        self.qBittorrent['actionafter'] = config.get(section, "action-after")
        self.qBittorrent['host'] = config.get(section, "host")
        self.qBittorrent['port'] = config.get(section, "port")
        self.qBittorrent['ssl'] = config.getboolean(section, "ssl")
        self.qBittorrent['username'] = config.get(section, "username")
        self.qBittorrent['password'] = config.get(section, "password")
        self.qBittorrent['path-mapping'] = config.getdict(section, "path-mapping", dictseparator="=", lower=False, replace=[])

        # Read relevant uTorrent section information
        section = "uTorrent"
        self.uTorrent = {}
        self.uTorrent['sb'] = config.get(section, "sickbeard-label").lower()
        self.uTorrent['sr'] = config.get(section, "sickrage-label").lower()
        self.uTorrent['sonarr'] = config.get(section, "sonarr-label").lower()
        self.uTorrent['radarr'] = config.get(section, "radarr-label").lower()
        self.uTorrent['bypass'] = config.get(section, "bypass-label").lower()
        self.uTorrent['convert'] = config.getboolean(section, "convert")
        self.uTorrent['output-dir'] = config.getdirectory(section, "output-directory")
        self.uTorrent['webui'] = config.getboolean(section, "webui")
        self.uTorrent['actionbefore'] = config.get(section, "action-before")
        self.uTorrent['actionafter'] = config.get(section, "action-after")
        self.uTorrent['host'] = config.get(section, "host")
        self.uTorrent['port'] = config.get(section, "port")
        self.uTorrent['ssl'] = config.getboolean(section, "ssl")
        self.uTorrent['username'] = config.get(section, "username")
        self.uTorrent['password'] = config.get(section, "password")
        self.uTorrent['path-mapping'] = config.getdict(section, "path-mapping", dictseparator="=", lower=False, replace=[])

        # Plex
        section = "Plex"
        self.Plex = {}
        self.Plex['username'] = config.get(section, "username")
        self.Plex['password'] = config.get(section, "password")
        self.Plex['servername'] = config.get(section, "servername")
        self.Plex['host'] = config.get(section, "host")
        self.Plex['port'] = config.getint(section, "port")
        self.Plex['refresh'] = config.getboolean(section, "refresh")
        self.Plex['token'] = config.get(section, "token")
        self.Plex['ssl'] = config.getboolean(section, "ssl")
        self.Plex['ignore-certs'] = config.getboolean(section, 'ignore-certs')
        self.Plex['path-mapping'] = config.getdict(section, "path-mapping", dictseparator="=", lower=False, replace=[])

    def writeConfig(self, config, cfgfile):
        if not os.path.isdir(os.path.dirname(cfgfile)):
            os.makedirs(os.path.dirname(cfgfile))
        try:
            fp = open(cfgfile, "w")
            config.write(fp)
            fp.close()
        except PermissionError:
            self.log.exception("Error writing to %s due to permissions." % (self.CONFIG_DEFAULT))
        except IOError:
            self.log.exception("Error writing to %s." % (self.CONFIG_DEFAULT))

    def migrateFromOld(self, config, configFile):
        try:
            write = False
            if config.has_option("Converter", "sort-streams"):
                if not config.getboolean("Converter", "sort-streams"):
                    config.remove_option("Converter", "sort-streams")
                    config.set("Audio.Sorting", "sorting", "")
                    config.set("Subtitle.Sorting", "sorting", "")
                    write = True
            elif config.has_option("Audio", "prefer-more-channels"):
                asorting = config.get("Audio.Sorting", 'sorting').lower()
                if config.getboolean("Audio", "prefer-more-channels"):
                    if "channels" in asorting and "channels.a" not in asorting and "channels.d" not in asorting:
                        asorting = asorting.replace("channels", "channels.d")
                        self.log.debug("Replacing channels with channels.d based on deprecated settings [prefer-more-channels: True].")
                    else:
                        asorting = asorting.replace("channels.a", "channels.d")
                        self.log.debug("Replacing channels.a with channels.d based on deprecated settings [prefer-more-channels: True].")
                else:
                    asorting = asorting.replace("channels.d", "channels.a")
                    self.log.debug("Replacing channels.d with channels.a based on deprecated settings [prefer-more-channels: False].")
                config.remove_option("Audio", "prefer-more-channels")
                config.set("Audio.Sorting", "sorting", asorting)
                write = True

            if config.has_option("Audio", "default-more-channels"):
                adsorting = config.get("Audio.Sorting", 'default-sorting').lower()
                if config.getboolean("Audio", "default-more-channels"):
                    if "channels" in adsorting and "channels.a" not in adsorting and "channels.d" not in adsorting:
                        adsorting = adsorting.replace("channels", "channels.d")
                        self.log.debug("Replacing channels with channels.d based on deprecated settings [default-more-channels: True].")
                    else:
                        adsorting = adsorting.replace("channels.a", "channels.d")
                        self.log.debug("Replacing channels.a with channels.d based on deprecated settings [default-more-channels: True].")
                else:
                    adsorting = adsorting.replace("channels.d", "channels.a")
                    self.log.debug("Replacing channels.d with channels.a based on deprecated settings [default-more-channels: False].")
                config.remove_option("Audio", "default-more-channels")
                config.set("Audio.Sorting", "default-sorting", adsorting)
                write = True

            if config.has_option("Audio.Sorting", "final-sort") and config.has_option("Audio.Sorting", "sorting") and config.getboolean("Audio.Sorting", "final-sort"):
                config.remove_option("Audio.Sorting", "final-sort")
                asort = config.getlist("Audio.Sorting", "sorting")
                if "map" not in asort:
                    asort.append("map")
                    config.set("Audio.Sorting", "sorting", "".join("%s, " % x for x in asort)[:-2])
                    self.log.debug("Final-sort is deprecated, adding to sorting list [audio.sorting-final-sort: True].")
                else:
                    self.log.debug("Final-sort is deprecated, removing [audio.sorting-final-sort: True].")
                write = True
            elif config.has_option("Audio.Sorting", "final-sort"):
                config.remove_option("Audio.Sorting", "final-sort")
                self.log.debug("Final-sort is deprecated, removing [audio.sorting-final-sort: False].")
                write = True

            if config.has_option("Audio", "copy-original-before"):
                config.remove_option("Audio", "copy-original-before")
                write = True

            if config.has_option("Universal Audio", "move-after"):
                config.remove_option("Universal Audio", "move-after")
                write = True

            if write:
                self.writeConfig(config, configFile)
        except:
            self.log.exception("Unable to migrate old sorting options.")
        return config
