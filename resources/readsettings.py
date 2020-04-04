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
            return default

        value = value.split(separator)

        for r in replace:
            value = [x.replace(r, '') for x in value]
        if lower:
            value = [x.lower() for x in value]

        value = [x.strip() for x in value]
        return value

    def getpath(self, section, option, vars=None):
        path = self.get(section, option, vars=vars).strip()
        if path == '':
            return None
        return os.path.normpath(path)

    def getdirectory(self, section, option, vars=None):
        directory = self.getpath(section, option, vars)
        try:
            os.path.makedirs(directory)
        except:
            pass
        return directory

    def getdirectories(self, section, option, vars=None, separator=",", default=[]):
        directories = self.getlist(section, option, vars=vars, separator=separator, default=default, lower=False)
        directories = [os.path.normpath(x) for x in directories]
        for d in directories:
            if not os.path.isdir(d):
                try:
                    os.path.makedirs(d)
                except:
                    pass
        return directories

    def getextension(self, section, option, vars=None):
        extension = self.get(section, option, vars=vars).lower().replace(' ', '').replace('.', '')
        if extension == '':
            return None
        return extension

    def getint(self, section, option, vars=None):
        if sys.version[0] == '2':
            return int(super(SMAConfigParser, self).get(section, option, vars=vars))
        return super(SMAConfigParser, self).getint(section, option, vars=vars)


class ReadSettings:
    defaults = {
        'Converter': {
            'ffmpeg': 'ffmpeg' if os.name != 'nt' else 'ffmpeg.exe',
            'ffprobe': 'ffprobe' if os.name != 'nt' else 'ffprobe.exe',
            'threads': 0,
            'hwaccels': 'dxva2, cuvid, qsv, d3d11va',
            'hwaccel-decoders': 'h264_cuvid, mjpeg_cuvid, mpeg1_cuvid, mpeg2_cuvid, mpeg4_cuvid, vc1_cuvid, hevc_qsv, h264_qsv',
            'output-directory': '',
            'output-format': 'mp4',
            'output-extension': 'mp4',
            'temp-extension': '',
            'minimum-size': '0',
            'ignored-extensions': 'nfo, ds_store',
            'copy-to': '',
            'move-to': '',
            'delete-original': True,
            'sort-streams': True,
            'process-same-extensions': False,
            'force-convert': False,
            'post-process': False,
            'preopts': '',
            'postopts': '',
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
        },
        'Video': {
            'codec': 'h264, x264',
            'max-bitrate': 0,
            'crf': -1,
            'crf-profiles': '',
            'max-width': 0,
            'profile': '',
            'max-level': 0.0,
            'pix-fmt': '',
        },
        'Audio': {
            'codec': 'ac3',
            'languages': '',
            'default-language': '',
            'first-stream-of-language': False,
            'allow-language-relax': True,
            'channel-bitrate': 128,
            'max-bitrate': 0,
            'max-channels': 0,
            'prefer-more-channels': True,
            'default-more-channels': True,
            'filter': '',
            'sample-rates': '',
            'copy-original': False,
            'aac-adtstoasc': False,
            'ignore-truehd': 'mp4, m4v',
        },
        'Universal Audio': {
            'codec': 'aac',
            'channel-bitrate': 128,
            'first-stream-only': False,
            'move-after': False,
            'filter': '',
        },
        'Subtitle': {
            'codec': 'mov_text',
            'codec-image-based': '',
            'languages': '',
            'default-language': '',
            'first-stream-of-language': False,
            'encoding': '',
            'burn-subtitles': False,
            'burn-dispositions': '',
            'download-subs': False,
            'download-hearing-impaired-subs': False,
            'download-providers': '',
            'embed-subs': True,
            'embed-image-subs': False,
            'embed-only-internal-subs': False,
            'filename-dispositions': 'forced',
            'ignore-embedded-subs': False,
            'attachment-codec': '',
        },
        'Sonarr': {
            'host': 'localhost',
            'port': 8989,
            'apikey': '',
            'ssl': False,
            'webroot': '',
        },
        'Radarr': {
            'host': 'localhost',
            'port': 7878,
            'apikey': '',
            'ssl': False,
            'webroot': ''
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
        'CouchPotato': {
            'host': 'localhost',
            'port': 5050,
            'username': '',
            'password': '',
            'apikey': '',
            'delay': 65,
            'method': 'renamer',
            'delete-failed': False,
            'ssl': False,
            'webroot': '',
        },
        'SABNZBD': {
            'convert': True,
            'sickbeard-category': 'sickbeard',
            'sickrage-category': 'sickrage',
            'couchpotato-category': 'couchpotato',
            'sonarr-category': 'sonarr',
            'radarr-category': 'radarr',
            'bypass-category': 'bypass',
            'output-directory': '',
        },
        'Deluge': {
            'couchpotato-label': 'couchpotato',
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
        },
        'qBittorrent': {
            'couchpotato-label': 'couchpotato',
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
            'output-directory': ''
        },
        'uTorrent': {
            'couchpotato-label': 'couchpotato',
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
        },
        'Plex': {
            'host': 'localhost',
            'port': 32400,
            'refresh': False,
            'token': '',
        },
    }

    migration = {
        'MP4': {
            'ffmpeg': "Converter.ffmpeg",
            'ffprobe': "Converter.ffprobe",
            'threads': 'Converter.threads',
            'output_directory': 'Converter.output-directory',
            'copy_to': 'Converter.copy-to',
            'move_to': 'Converter.move-to',
            'output_extension': 'Converter.output-extension',
            'temp_extension': 'Converter.temp-extension',
            'output_format': 'Converter.output-format',
            'delete_original': 'Converter.delete-original',
            'relocate_moov': 'Metadata.relocate-moov',
            'ios-audio': 'Universal Audio.codec',
            'ios-first-track-only': 'Universal Audio.first-stream-only',
            'ios-move-last': 'Universal Audio.move-after',
            'ios-audio-filter': 'Universal Audio.filter',
            'max-audio-channels': 'Audio.max-channels',
            'audio-language': 'Audio.languages',
            'audio-default-language': 'Audio.default-language',
            'audio-codec': 'Audio.codec',
            'ignore-truehd': 'Audio.ignore-truehd',
            'audio-filter': 'Audio.filter',
            'audio-sample-rates': 'Audio.sample-rates',
            'audio-channel-bitrate': 'Audio.channel-bitrate',
            'audio-copy-original': 'Audio.copy-original',
            'audio-first-track-of-language': 'Audio.first-stream-of-language',
            'allow-audio-language-relax': 'Audio.allow-language-relax',
            'sort-streams': 'Converter.sort-streams',
            'prefer-more-channels': 'Audio.prefer-more-channels',
            'video-codec': 'Video.codec',
            'video-bitrate': 'Video.max-bitrate',
            'video-crf': 'Video.crf',
            'video-crf-profiles': 'Video.crf-profiles',
            'video-max-width': 'Video.max-width',
            'video-profile': 'Video.profile',
            'h264-max-level': 'Video.max-level',
            'aac_adtstoasc': 'Audio.aac-adtstoasc',
            'hwaccels': 'Converter.hwaccels',
            'hwaccel-decoders': 'Converter.hwaccel-decoders',
            'subtitle-codec': 'Subtitle.codec',
            'subtitle-codec-image-based': 'Subtitle.codec-image-based',
            'subtitle-language': 'Subtitle.languages',
            'subtitle-default-language': 'Subtitle.default-language',
            'subtitle-encoding': 'Subtitle.encoding',
            'burn-subtitles': 'Subtitle.burn-subtitles',
            'attachment-codec': 'Subtitle.attachment-codec',
            'process-same-extensions': 'Converter.process-same-extensions',
            'force-convert': 'Converter.force-convert',
            'fullpathguess': 'Metadata.full-path-guess',
            'tagfile': 'Metadata.tag',
            'tag-language': 'Metadata.tag-language',
            'download-artwork': 'Metadata.download-artwork',
            'download-subs': 'Subtitle.download-subs',
            'download-hearing-impaired-subs': 'Subtitle.download-hearing-impaired-subs',
            'embed-subs': 'Subtitle.embed-subs',
            'embed-image-subs': 'Subtitle.embed-image-subs',
            'embed-only-internal-subs': 'Subtitle.embed-only-internal-subs',
            'sub-providers': 'Subtitle.download-providers',
            'post-process': 'Converter.post-process',
            'ignored-extensions': 'Converter.ignored-extensions',
            'pix-fmt': 'Video.pix-fmt',
            'preopts': 'Converter.preopts',
            'postopts': 'Converter.postopts',
        },
        'SickBeard': {
            'host': 'Sickbeard.host',
            'port': 'Sickbeard.port',
            'ssl': "Sickbeard.ssl",
            'api_key': 'Sickbeard.apikey',
            'web_root': 'Sickbeard.webroot',
            'username': 'Sickbeard.username',
            'password': 'Sickbeard.password'
        },
        'CouchPotato': {
            'host': 'CouchPotato.host',
            'port': 'CouchPotato.port',
            'username': 'CouchPotato.username',
            'password': 'CouchPotato.password',
            'apikey': 'CouchPotato.apikey',
            'delay': 'CouchPotato.delay',
            'method': 'CouchPotato.method',
            'delete_failed': 'CouchPotato.delete-failed',
            'ssl': 'CouchPotato.ssl',
            'web_root': 'CouchPotato.webroot',
        },
        'Sonarr': {
            'host': 'Sonarr.host',
            'port': 'Sonarr.port',
            'apikey': 'Sonarr.apikey',
            'ssl': 'Sonarr.ssl',
            'web_root': 'Sonarr.webroot',
        },
        "Radarr": {
            'host': 'Radarr.host',
            'port': 'Radarr.port',
            'apikey': 'Radarr.apikey',
            'ssl': 'Radarr.ssl',
            'web_root': 'Radarr.webroot',
        },
        'uTorrent': {
            'couchpotato-label': 'uTorrent.couchpotato-label',
            'sickbeard-label': 'uTorrent.sickbeard-label',
            'sickrage-label': 'uTorrent.sickrage-label',
            'sonarr-label': 'uTorrent.sonarr-label',
            'radarr-label': 'uTorrent.radarr-label',
            'bypass-label': 'uTorrent.bypass-label',
            'convert': 'uTorrent.convert',
            'webui': 'uTorrent.webui',
            'action_before': 'uTorrent.action-before',
            'action_after': 'uTorrent.action-after',
            'host': 'uTorrent.host',
            'username': 'uTorrent.username',
            'password': 'uTorrent.password',
            'output_directory': 'uTorrent.output-directory',
        },
        "SABNZBD": {
            'convert': 'SABNZBD.convert',
            'sickbeard-category': 'SABNZBD.sickbeard-category',
            'sickrage-category': 'SABNZBD.sickrage-category',
            'couchpotato-category': 'SABNZBD.couchpotato-category',
            'sonarr-category': 'SABNZBD.sonarr-category',
            'radarr-category': 'SABNZBD.radarr-category',
            'bypass-category': 'SABNZBD.bypass-category',
            'output_directory': 'SABNZBD.output-directory',
        },
        "Sickrage": {
            'host': 'Sickrage.host',
            'port': 'Sickrage.port',
            'ssl': "Sickrage.ssl",
            'api_key': 'Sickrage.apikey',
            'web_root': 'Sickrage.webroot',
            'username': 'Sickrage.username',
            'password': 'Sickrage.password',
        },
        "Deluge": {
            'couchpotato-label': 'Deluge.couchpotato-label',
            'sickbeard-label': 'Deluge.sickbeard-label',
            'sickrage-label': 'Deluge.sickrage-label',
            'sonarr-label': 'Deluge.sonarr-label',
            'radarr-label': 'Deluge.radarr-label',
            'bypass-label': 'Deluge.bypass-label',
            'convert': 'Deluge.convert',
            'host': 'Deluge.host',
            'port': 'Deluge.port',
            'username': 'Deluge.username',
            'password': 'Deluge.password',
            'output_directory': 'Deluge.output-directory',
            'remove': 'Deluge.remove',
        },
        "qBittorrent": {
            'couchpotato-label': 'qBittorrent.couchpotato-label',
            'sickbeard-label': 'qBittorrent.sickbeard-label',
            'sickrage-label': 'qBittorrent.sickrage-label',
            'sonarr-label': 'qBittorrent.sonarr-label',
            'radarr-label': 'qBittorrent.radarr-label',
            'bypass-label': 'qBittorrent.bypass-label',
            'convert': 'qBittorrent.convert',
            'action_before': 'qBittorrent.action-before',
            'action_after': 'qBittorrent.action-after',
            'host': 'qBittorrent.host',
            'username': 'qBittorrent.username',
            'password': 'qBittorrent.password',
            'output_directory': 'qBittorrent.output-directory',
        },
        "Plex": {
            'host': 'Plex.host',
            'port': 'Plex.port',
            'refresh': 'Plex.refresh',
            'token': 'Plex.token'
        },
        "Permissions": {
            'chmod': 'Permissions.chmod',
            'uid': 'Permissions.uid',
            'gid': 'Permissions.gid'
        }
    }

    def __init__(self, configFile=None, logger=None):
        self.log = logger or logging.getLogger(__name__)

        self.log.info(sys.executable)
        if sys.version_info.major == 2:
            self.log.warning("Python 2 is no longer officially supported. Use with caution.")

        defaultConfigFile = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../config/autoProcess.ini"))
        oldConfigFile = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../autoProcess.ini"))
        envConfigFile = os.environ.get("SMA_CONFIG")

        if envConfigFile and os.path.exists(os.path.realpath(envConfigFile)):
            configFile = os.path.realpath(envConfigFile)
            self.log.debug("SMACONFIG environment variable override found.")
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
            new = os.path.realpath(os.path.join(os.path.join(configFile, "config"), "autoProcess.ini"))
            old = os.path.realpath(os.path.join(configFile, "autoProcess.ini"))
            if not os.path.exists(new) and os.path.exists(old):
                configFile = old
            else:
                configFile = new
            self.log.debug("ConfigFile specified is a directory, joining with autoProcess.ini.")

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
            config.read(configFile)
        else:
            self.log.error("Config file not found, creating %s." % configFile)
            # config.filename = filename
            write = True

        config = self.migrateFromOld(config, configFile)

        # Make sure all sections and all keys for each section are present
        for s in self.defaults:
            if not config.has_section(s):
                config.add_section(s)
                write = True
            for k in self.defaults[s]:
                if not config.has_option(s, k):
                    config.set(s, k, str(self.defaults[s][k]))
                    write = True

        # If any keys are missing from the config file, write them
        if write:
            self.writeConfig(config, configFile)

        self.readConfig(config)

    def readConfig(self, config):
        # Main converter settings
        section = "Converter"
        self.ffmpeg = config.getpath(section, 'ffmpeg', vars=os.environ)
        self.ffprobe = config.getpath(section, 'ffprobe', vars=os.environ)
        self.threads = config.getint(section, 'threads')
        self.hwaccels = config.getlist(section, 'hwaccels')
        self.hwaccel_decoders = config.getlist(section, "hwaccel-decoders")
        self.output_dir = config.getdirectory(section, "output-directory")
        self.output_format = config.get(section, "output-format")
        self.output_extension = config.getextension(section, "output-extension")
        self.temp_extension = config.getextension(section, "temp-extension")
        self.minimum_size = config.getint(section, "minimum-size")
        self.ignored_extensions = config.getlist(section, 'ignored-extensions', replace=[' ', '.'])
        self.copyto = config.getdirectories(section, "copy-to", separator='|')
        self.moveto = config.getdirectory(section, "move-to")
        self.delete = config.getboolean(section, "delete-original")
        self.sort_streams = config.getboolean(section, "sort-streams")
        self.process_same_extensions = config.getboolean(section, "process-same-extensions")
        self.force_convert = config.getboolean(section, "force-convert")
        self.postprocess = config.getboolean(section, 'post-process')
        self.preopts = config.getlist(section, "preopts")
        self.postopts = config.getlist(section, "postopts")

        if self.force_convert:
            self.process_same_extensions = True
            self.log.warning("Force-convert is true, so convert-mp4 is being overridden to true as well")

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
        self.sanitizedisposition = config.getlist(section, "sanitize-disposition")

        # Video
        section = "Video"
        self.vcodec = config.getlist(section, "codec")
        self.vmaxbitrate = config.getint(section, "max-bitrate")
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

        self.vwidth = config.getint(section, "max-width")
        self.video_level = config.getfloat(section, "max-level")
        self.vprofile = config.getlist(section, "profile")
        self.pix_fmt = config.getlist(section, "pix-fmt")

        # Audio
        section = "Audio"
        self.acodec = config.getlist(section, "codec")
        self.awl = config.getlist(section, 'languages')
        self.adl = config.get(section, 'default-language').lower()
        self.abitrate = config.getint(section, "channel-bitrate")
        self.amaxbitrate = config.getint(section, 'max-bitrate')
        self.maxchannels = config.getint(section, 'max-channels')
        self.prefer_more_channels = config.getboolean(section, "prefer-more-channels")
        self.default_more_channels = config.getboolean(section, "default-more-channels")
        self.afilter = config.get(section, "filter")
        self.audio_samplerates = [int(x) for x in config.getlist(section, "sample-rates") if x.isdigit()]
        self.audio_copyoriginal = config.getboolean(section, "copy-original")
        self.audio_first_language_stream = config.getboolean(section, "first-stream-of-language")
        self.allow_language_relax = config.getboolean(section, "allow-language-relax")
        self.aac_adtstoasc = config.getboolean(section, 'aac-adtstoasc')
        self.ignore_truehd = config.getextension(section, "ignore-truehd")

        # Universal Audio
        section = "Universal Audio"
        self.ua = config.getlist(section, "codec")
        self.ua_bitrate = config.getint(section, "channel-bitrate")
        self.ua_first_only = config.getboolean(section, "first-stream-only")
        self.ua_last = config.getboolean(section, "move-after")
        self.ua_filter = config.get(section, "filter")

        # Subtitles
        section = "Subtitle"
        self.scodec = config.getlist(section, 'codec')
        self.scodec_image = config.getlist(section, 'codec-image-based')
        self.swl = config.getlist(section, 'languages')
        self.sdl = config.get(section, 'default-language').lower()
        self.sub_first_language_stream = config.getboolean(section, "first-stream-of-language")
        self.subencoding = config.get(section, 'encoding')
        self.burn_subtitles = config.getboolean(section, "burn-subtitles")
        self.burn_dispositions = config.getlist(section, "burn-dispositions")
        self.downloadsubs = config.getboolean(section, "download-subs")
        self.hearing_impaired = config.getboolean(section, 'download-hearing-impaired-subs')
        self.subproviders = config.getlist(section, 'download-providers')
        self.embedsubs = config.getboolean(section, 'embed-subs')
        self.embedimgsubs = config.getboolean(section, 'embed-image-subs')
        self.embedonlyinternalsubs = config.getboolean(section, 'embed-only-internal-subs')
        self.filename_dispositions = config.getlist(section, "filename-dispositions")
        self.ignore_embedded_subs = config.getboolean(section, 'ignore-embedded-subs')
        self.attachmentcodec = config.getlist(section, 'attachment-codec')

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

        # Read relevant CouchPotato section information
        section = "CouchPotato"
        self.CP = {}
        self.CP['host'] = config.get(section, "host")
        self.CP['port'] = config.getint(section, "port")
        self.CP['username'] = config.get(section, "username")
        self.CP['password'] = config.get(section, "password")
        self.CP['apikey'] = config.get(section, "apikey")
        self.CP['delay'] = config.getfloat(section, "delay")
        self.CP['method'] = config.get(section, "method")
        self.CP['webroot'] = config.get(section, "webroot")
        self.CP['delete_failed'] = config.getboolean(section, "delete-failed")
        self.CP['ssl'] = config.getboolean(section, 'ssl')

        # SAB
        section = "SABNZBD"
        self.SAB = {}
        self.SAB['convert'] = config.getboolean(section, "convert")
        self.SAB['cp'] = config.get(section, "Couchpotato-category").lower()
        self.SAB['sb'] = config.get(section, "Sickbeard-category").lower()
        self.SAB['sr'] = config.get(section, "Sickrage-category").lower()
        self.SAB['sonarr'] = config.get(section, "Sonarr-category").lower()
        self.SAB['radarr'] = config.get(section, "Radarr-category").lower()
        self.SAB['bypass'] = config.get(section, "Bypass-category").lower()
        self.SAB['output_dir'] = config.getdirectory(section, "output-directory")

        # Deluge
        section = "Deluge"
        self.deluge = {}
        self.deluge['cp'] = config.get(section, "couchpotato-label").lower()
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
        self.deluge['output_dir'] = config.getdirectory(section, "output-directory")
        self.deluge['remove'] = config.getboolean(section, "remove")

        # qBittorrent
        section = "qBittorrent"
        self.qBittorrent = {}
        self.qBittorrent['cp'] = config.get(section, "couchpotato-label").lower()
        self.qBittorrent['sb'] = config.get(section, "sickbeard-label").lower()
        self.qBittorrent['sr'] = config.get(section, "sickrage-label").lower()
        self.qBittorrent['sonarr'] = config.get(section, "sonarr-label").lower()
        self.qBittorrent['radarr'] = config.get(section, "radarr-label").lower()
        self.qBittorrent['bypass'] = config.get(section, "bypass-label").lower()
        self.qBittorrent['convert'] = config.getboolean(section, "convert")
        self.qBittorrent['output_dir'] = config.getdirectory(section, "output-directory")
        self.qBittorrent['actionbefore'] = config.get(section, "action-before")
        self.qBittorrent['actionafter'] = config.get(section, "action-after")
        self.qBittorrent['host'] = config.get(section, "host")
        self.qBittorrent['port'] = config.get(section, "port")
        self.qBittorrent['ssl'] = config.getboolean(section, "ssl")
        self.qBittorrent['username'] = config.get(section, "username")
        self.qBittorrent['password'] = config.get(section, "password")

        # Read relevant uTorrent section information
        section = "uTorrent"
        self.uTorrent = {}
        self.uTorrent['cp'] = config.get(section, "couchpotato-label").lower()
        self.uTorrent['sb'] = config.get(section, "sickbeard-label").lower()
        self.uTorrent['sr'] = config.get(section, "sickrage-label").lower()
        self.uTorrent['sonarr'] = config.get(section, "sonarr-label").lower()
        self.uTorrent['radarr'] = config.get(section, "radarr-label").lower()
        self.uTorrent['bypass'] = config.get(section, "bypass-label").lower()
        self.uTorrent['convert'] = config.getboolean(section, "convert")
        self.uTorrent['output_dir'] = config.getdirectory(section, "output-directory")
        self.uTorrent['webui'] = config.getboolean(section, "webui")
        self.uTorrent['actionbefore'] = config.get(section, "action-before")
        self.uTorrent['actionafter'] = config.get(section, "action-after")
        self.uTorrent['host'] = config.get(section, "host")
        self.uTorrent['port'] = config.get(section, "port")
        self.uTorrent['ssl'] = config.getboolean(section, "ssl")
        self.uTorrent['username'] = config.get(section, "username")
        self.uTorrent['password'] = config.get(section, "password")

        # Plex
        section = "Plex"
        self.Plex = {}
        self.Plex['host'] = config.get(section, "host")
        self.Plex['port'] = config.getint(section, "port")
        self.Plex['refresh'] = config.getboolean(section, "refresh")
        self.Plex['token'] = config.get(section, "token")

    def writeConfig(self, config, cfgfile):
        if not os.path.isdir(os.path.dirname(cfgfile)):
            os.mkdir(os.path.dirname(cfgfile))
        try:
            fp = open(cfgfile, "w")
            config.write(fp)
            fp.close()
        except IOError:
            self.log.exception("Error writing to autoProcess.ini.")
        except PermissionError:
            self.log.exception("Error writing to autoProcess.ini due to permissions.")

    def migrateFromOld(self, config, configFile):
        if config.has_section("MP4"):
            self.log.info("Old configuration file format found, attempting to migrate to new format.")
            backup = configFile + ".backup"
            i = 2
            while os.path.exists(backup):
                backup = configFile + "." + str(i) + ".backup"
                i += 1
            import shutil
            shutil.copy(configFile, backup)
            self.log.info("Old configuration file backed up to %s" % backup)

            open(configFile, 'w').close()
            new = {}

            self.log.info("Begining Conversion")
            self.log.info("==========================")
            for section in config.sections():
                for (key, val) in config.items(section, raw=True):
                    try:
                        newsection, newkey = self.migration[section][key].split(".")
                    except:
                        self.log.error("%s.%s >> No destination" % (section, key))
                        continue

                    if newsection not in new:
                        new[newsection] = {}
                        self.log.debug("%s section created" % newsection)
                    default = self.defaults[newsection][newkey]
                    if section in ['uTorrent', 'qBittorrent'] and key == 'host':
                        try:
                            ssl = ('https' in val)
                            val = val.replace("https://", "").replace("http://", "").replace("/", "")
                            val, port = val.split(':')
                            new[newsection]['port'] = int(port)
                            new[newsection]['ssl'] = ssl
                            self.log.info("%s.%s >> %s.%s | %s (%s)" % (section, key, newsection, "port", port, type(port).__name__))
                            self.log.info("%s.%s >> %s.%s | %s (%s)" % (section, key, newsection, "ssl", ssl, type(ssl).__name__))
                        except:
                            val = self.defaults[newsection][newkey]
                    elif section == 'MP4' and key == 'ios-audio':
                        if val.lower() in ['true', 't', 'yes']:
                            val = self.defaults[newsection][newkey]
                        elif val.lower() in ['false', 'f', 'no']:
                            val = ''
                    elif key == 'ignore-truehd':
                        if val.lower() in ['true', 't', 'yes']:
                            val = self.defaults[newsection][newkey]
                        else:
                            val = ''
                    elif not isinstance(val, type(default)) and '%' not in val:
                        try:
                            if isinstance(default, bool):
                                val = (val.lower() in ['true', 't', 'yes'])
                            elif isinstance(default, float):
                                val = float(val)
                            elif isinstance(default, int):
                                val = int(val)
                        except:
                            self.log.error("** %s.%s unable to convert %s (%s) to type %s, using default value %s" % (section, key, val, type(val).__name__, type(default).__name__, self.defaults[newsection][newkey]))
                            val = self.defaults[newsection][newkey]

                    self.log.info("%s.%s >> %s.%s | %s (%s)" % (section, key, newsection, newkey, val, type(val).__name__))
                    new[newsection][newkey] = val

            newconfig = SMAConfigParser()
            for s in new:
                if not newconfig.has_section(s):
                    newconfig.add_section(s)
                    write = True
                for k in new[s]:
                    if not newconfig.has_option(s, k):
                        newconfig.set(s, k, str(new[s][k]))
            self.writeConfig(newconfig, configFile)
            return newconfig
        return config
