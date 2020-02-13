import os
import sys
import locale

try:
    import configparser
except ImportError:
    import ConfigParser as configparser
try:
    from importlib import reload
except ImportError:
    pass
import logging
from extensions import *


class ReadSettings:
    log = logging.getLogger(__name__)
    def __init__(self, directory, filename, logger=None):

        # Setup logging
        if logger:
            self.log = logger

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

        self.log.info(sys.executable)

        # Default settings for SickBeard
        sb_defaults = {'host': 'localhost',
                       'port': '8081',
                       'ssl': "False",
                       'api_key': '',
                       'web_root': '',
                       'username': '',
                       'password': ''}

        ffmpeg = 'ffmpeg'
        ffprobe = 'ffprobe'
        if os.name == 'nt':
            ffmpeg = 'ffmpeg.exe'
            ffprobe = 'ffprobe.exe'

        # Default MP4 conversion settings
        mp4_defaults = {'ffmpeg': ffmpeg,
                        'ffprobe': ffprobe,
                        'threads': '0',
                        'output_directory': '',
                        'copy_to': '',
                        'move_to': '',
                        'output_extension': 'mp4',
                        'temp_extension': '',
                        'output_format': 'mp4',
                        'delete_original': 'True',
                        'relocate_moov': 'True',
                        'ios-audio': 'True',
                        'ios-first-track-only': 'False',
                        'ios-move-last': 'False',
                        'ios-audio-filter': '',
                        'max-audio-channels': '',
                        'audio-language': '',
                        'audio-default-language': '',
                        'audio-codec': 'ac3',
                        'ignore-truehd': 'True',
                        'audio-filter': '',
                        'audio-channel-bitrate': '256',
                        'audio-copy-original': 'False',
                        'audio-first-track-of-language': 'False',
                        'allow-audio-language-relax': 'True',
                        'sort-streams': 'False',
                        'prefer-more-channels': 'True',
                        'video-codec': 'h264, x264',
                        'video-bitrate': '',
                        'video-crf': '',
                        'video-max-width': '',
                        'video-profile': '',
                        'h264-max-level': '',
                        'aac_adtstoasc': 'False',
                        'use-qsv-decoder-with-encoder': 'True',
                        'use-hevc-qsv-decoder': 'False',
                        'enable_dxva2_gpu_decode': 'False',
                        'subtitle-codec': 'mov_text',
                        'subtitle-codec-image-based': '',
                        'subtitle-language': '',
                        'subtitle-default-language': '',
                        'subtitle-encoding': '',
                        'burn-subtitles': 'False',
                        'process-same-extensions': 'False',
                        'force-convert': 'False',
                        'fullpathguess': 'True',
                        'tagfile': 'True',
                        'tag-language': 'en',
                        'download-artwork': 'poster',
                        'download-subs': 'False',
                        'download-hearing-impaired-subs': 'False',
                        'embed-subs': 'True',
                        'embed-only-internal-subs': 'False',
                        'sub-providers': '',
                        'post-process': 'False',
                        'pix-fmt': '',
                        'preopts': '',
                        'postopts': ''}
        # Default settings for CouchPotato
        cp_defaults = {'host': 'localhost',
                       'port': '5050',
                       'username': '',
                       'password': '',
                       'apikey': '',
                       'delay': '65',
                       'method': 'renamer',
                       'delete_failed': 'False',
                       'ssl': 'False',
                       'web_root': ''}
        # Default settings for Sonarr
        sonarr_defaults = {'host': 'localhost',
                           'port': '8989',
                           'apikey': '',
                           'ssl': 'False',
                           'web_root': ''}
        # Default settings for Radarr
        radarr_defaults = {'host': 'localhost',
                           'port': '7878',
                           'apikey': '',
                           'ssl': 'False',
                           'web_root': ''}
        # Default uTorrent settings
        utorrent_defaults = {'couchpotato-label': 'couchpotato',
                             'sickbeard-label': 'sickbeard',
                             'sickrage-label': 'sickrage',
                             'sonarr-label': 'sonarr',
                             'radarr-label': 'radarr',
                             'bypass-label': 'bypass',
                             'convert': 'True',
                             'webui': 'False',
                             'action_before': 'stop',
                             'action_after': 'removedata',
                             'host': 'http://localhost:8080/',
                             'username': '',
                             'password': '',
                             'output_directory': ''}
        # Default SAB settings
        sab_defaults = {'convert': 'True',
                        'Sickbeard-category': 'sickbeard',
                        'Sickrage-category': 'sickrage',
                        'Couchpotato-category': 'couchpotato',
                        'Sonarr-category': 'sonarr',
                        'Radarr-category': 'radarr',
                        'Bypass-category': 'bypass',
                        'output_directory': ''}
        # Default Sickrage Settings
        sr_defaults = {'host': 'localhost',
                       'port': '8081',
                       'ssl': "False",
                       'api_key': '',
                       'web_root': '',
                       'username': '',
                       'password': ''}

        # Default deluge settings
        deluge_defaults = {'couchpotato-label': 'couchpotato',
                           'sickbeard-label': 'sickbeard',
                           'sickrage-label': 'sickrage',
                           'sonarr-label': 'sonarr',
                           'radarr-label': 'radarr',
                           'bypass-label': 'bypass',
                           'convert': 'True',
                           'host': 'localhost',
                           'port': '58846',
                           'username': '',
                           'password': '',
                           'output_directory': '',
                           'remove': 'false'}

        # Default QBT settings
        qbt_defaults = {'couchpotato-label': 'couchpotato',
                        'sickbeard-label': 'sickbeard',
                        'sickrage-label': 'sickrage',
                        'sonarr-label': 'sonarr',
                        'radarr-label': 'radarr',
                        'bypass-label': 'bypass',
                        'convert': 'True',
                        'action_before': '',
                        'action_after': '',
                        'host': 'http://localhost:8080/',
                        'username': '',
                        'password': '',
                        'output_directory': ''}

        # Default Plex Settings
        plex_defaults = {'host': 'localhost',
                         'port': '32400',
                         'refresh': 'true',
                         'token': ''}

        # Permissions
        permissions_defaults = {'chmod': '0755',
                                'uid': '-1',
                                'gid': '-1'}

        defaults = {'SickBeard': sb_defaults, 'CouchPotato': cp_defaults, 'Sonarr': sonarr_defaults, 'Radarr': radarr_defaults, 'MP4': mp4_defaults, 'uTorrent': utorrent_defaults, 'qBittorrent': qbt_defaults, 'SABNZBD': sab_defaults, 'Sickrage': sr_defaults, 'Deluge': deluge_defaults, 'Plex': plex_defaults, 'Permissions': permissions_defaults}
        write = False  # Will be changed to true if a value is missing from the config file and needs to be written

        config = configparser.SafeConfigParser()
        configFile = os.path.join(directory, filename)
        if os.path.isfile(configFile):
            config.read(configFile)
        else:
            self.log.error("Config file not found, creating %s." % configFile)
            # config.filename = filename
            write = True

        # Make sure all sections and all keys for each section are present
        for s in defaults:
            if not config.has_section(s):
                config.add_section(s)
                write = True
            for k in defaults[s]:
                if not config.has_option(s, k):
                    config.set(s, k, defaults[s][k])
                    write = True

        # If any keys are missing from the config file, write them
        if write:
            self.writeConfig(config, configFile)

        # Read relevant MP4 section information
        section = "MP4"
        self.ffmpeg = os.path.normpath(self.raw(config.get(section, "ffmpeg")))  # Location of FFMPEG.exe
        self.ffprobe = os.path.normpath(self.raw(config.get(section, "ffprobe")))  # Location of FFPROBE.exe
        self.threads = config.get(section, "threads")  # Number of FFMPEG threads
        try:
            int(self.threads)
        except:
            self.threads = "0"

        self.output_dir = config.get(section, "output_directory")
        if self.output_dir == '':
            self.output_dir = None
        else:
            self.output_dir = os.path.normpath(self.raw(self.output_dir))  # Output directory
        self.copyto = config.get(section, "copy_to")  # Directories to make copies of the final product
        if self.copyto == '':
            self.copyto = None
        else:
            self.copyto = self.copyto.split('|')
            for i in range(len(self.copyto)):
                self.copyto[i] = os.path.normpath(self.copyto[i])
                if not os.path.isdir(self.copyto[i]):
                    try:
                        os.makedirs(self.copyto[i])
                    except:
                        self.log.exception("Error making directory %s." % (self.copyto[i]))
        self.moveto = config.get(section, "move_to")  # Directory to move final product to
        if self.moveto == '':
            self.moveto = None
        else:
            self.moveto = os.path.normpath(self.moveto)
            if not os.path.isdir(self.moveto):
                try:
                    os.makedirs(self.moveto)
                except:
                    self.log.exception("Error making directory %s." % (self.moveto))
                    self.moveto = None

        self.output_extension = config.get(section, "output_extension")  # Output extension
        self.temp_extension = config.get(section, "temp_extension")  # Temporary extension used during processing
        if self.temp_extension == '':
            self.temp_extension = None
        elif self.temp_extension.startswith('.'):
            self.temp_extension = self.temp_extension[1:]
        self.output_format = config.get(section, "output_format")  # Output format
        self.delete = config.getboolean(section, "delete_original")  # Delete original file
        self.relocate_moov = config.getboolean(section, "relocate_moov")  # Relocate MOOV atom to start of file
        self.ignore_truehd = config.getboolean(section, "ignore-truehd")  # Ignore truehd
        if self.relocate_moov:
            try:
                import qtfaststart
            except:
                self.log.error("Please install QTFastStart via PIP, relocate_moov will be disabled without this module.")
                self.relocate_moov = False
        self.acodec = config.get(section, "audio-codec").lower()  # Gets the desired audio codec, if no valid codec selected, default to AC3
        if self.acodec == '':
            self.acodec == ['ac3']
        else:
            self.acodec = self.acodec.lower().replace(' ', '').split(',')

        self.abitrate = config.get(section, "audio-channel-bitrate")
        if self.abitrate == '':
            self.abitrate = 0
        else:
            try:
                self.abitrate = int(self.abitrate)
            except:
                self.abitrate = 256
                self.log.warning("Audio bitrate was invalid, defaulting to 256 per channel.")
        if self.abitrate > 256:
            self.log.warning("Audio bitrate >256 may create errors with common codecs.")

        self.audio_copyoriginal = config.getboolean(section, "audio-copy-original")  # Copies the original audio track regardless of format if a converted track is being generated

        self.afilter = config.get(section, "audio-filter").lower().strip()  # Audio filter
        if self.afilter == '':
            self.afilter = None

        self.audio_first_language_track = config.getboolean(section, "audio-first-track-of-language")  # Only take the first audio track in a whitelisted language, then no more

        self.allow_language_relax = config.getboolean(section, "allow-audio-language-relax")  # If not audio streams in the designed languages are found, allow the audio settings to relax to have some audio

        self.sort_streams = config.getboolean(section, "sort-streams")  # Reorders audio track output based on the listed languages and channels

        self.prefer_more_channels = config.getboolean(section, "prefer-more-channels")  # When choosing default audio track, prefer tracks with more channels

        self.iOS = config.get(section, "ios-audio").lower().strip()  # Creates a second audio channel if the standard output methods are different from this for iOS compatability
        if self.iOS == "" or self.iOS in ['false', 'no', 'f', '0']:
            self.iOS = False
        else:
            if self.iOS in ['true', 'yes', 't', '1']:
                self.iOS = ['aac']
            else:
                self.iOS = self.iOS.replace(' ', '').split(',')

        self.iOSFirst = config.getboolean(section, "ios-first-track-only")  # Enables the iOS audio option only for the first track

        self.iOSLast = config.getboolean(section, "ios-move-last")  # Moves the iOS audio track to the last in the series of tracks

        self.iOSfilter = config.get(section, "ios-audio-filter").lower().strip()  # iOS audio filter
        if self.iOSfilter == '':
            self.iOSfilter = None

        try:
            self.burn_subtitles = config.getboolean(section, "burn-subtitles")
            if self.burn_subtitles:
                self.burn_subtitles = "any"
        except:
            self.burn_subtitles = config.get(section, "burn-subtitles").lower().strip()  # Option to burn subtitles

        self.downloadsubs = config.getboolean(section, "download-subs")  # Enables downloading of subtitles from the internet sources using subliminal
        if self.downloadsubs:
            try:
                import subliminal
            except Exception as e:
                self.downloadsubs = False
                self.log.exception("Subliminal is not installed, automatically downloading of subs has been disabled.")
        self.subproviders = config.get(section, 'sub-providers').lower()
        if self.subproviders == '':
            self.subproviders = None
        else:
            self.subproviders = self.subproviders.lower().replace(' ', '').split(',')
        self.hearing_impaired = config.getboolean(section, 'download-hearing-impaired-subs')

        self.embedsubs = config.getboolean(section, 'embed-subs')

        self.embedonlyinternalsubs = config.getboolean(section, 'embed-only-internal-subs')

        try:
            self.postprocess = config.getboolean(section, 'post-process')
        except:
            self.postprocess = False

        self.aac_adtstoasc = config.getboolean(section, 'aac_adtstoasc')

        # Setup variable for maximum audio channels
        self.maxchannels = config.get(section, 'max-audio-channels')
        if self.maxchannels == "":
            self.maxchannels = None
        else:
            try:
                self.maxchannels = int(self.maxchannels)
            except:
                self.log.exception("Invalid number of audio channels specified.")
                self.maxchannels = None
        if self.maxchannels is not None and self.maxchannels < 1:
            self.log.warning("Must have at least 1 audio channel.")
            self.maxchannels = None

        self.vcodec = config.get(section, "video-codec")
        if self.vcodec == '':
            self.vcodec == ['h264', 'x264']
        else:
            self.vcodec = self.vcodec.lower().replace(' ', '').split(',')

        self.vbitrate = config.get(section, "video-bitrate")
        if self.vbitrate == '':
            self.vbitrate = None
        else:
            try:
                self.vbitrate = int(self.vbitrate)
                if not (self.vbitrate > 0):
                    self.vbitrate = None
                    self.log.warning("Video bitrate must be greater than 0, defaulting to no video bitrate cap.")
            except:
                self.log.exception("Invalid video bitrate, defaulting to no video bitrate cap.")
                self.vbitrate = None

        self.vcrf = config.get(section, "video-crf")
        if self.vcrf == '':
            self.vcrf = None
        else:
            try:
                self.vcrf = int(self.vcrf)
            except:
                self.log.exception("Invalid CRF setting, defaulting to none.")
                self.vcrf = None

        self.vwidth = config.get(section, "video-max-width")
        if self.vwidth == '':
            self.vwidth = None
        else:
            try:
                self.vwidth = int(self.vwidth)
            except:
                self.log.exception("Invalid video width, defaulting to none.")
                self.vwidth = None

        self.h264_level = config.get(section, "h264-max-level")
        if self.h264_level == '':
            self.h264_level = None
        else:
            try:
                self.h264_level = float(self.h264_level)
            except:
                self.log.exception("Invalid h264 level, defaulting to none.")
                self.h264_level = None

        self.vprofile = config.get(section, "video-profile")
        if self.vprofile == '':
            self.vprofile = None
        else:
            self.vprofile = self.vprofile.lower().strip().replace(' ', '').split(',')

        self.qsv_decoder = config.getboolean(section, "use-qsv-decoder-with-encoder")  # Use Intel QuickSync Decoder when using QuickSync Encoder
        self.hevc_qsv_decoder = config.getboolean(section, "use-hevc-qsv-decoder")  # only supported on 6th gen intel and up.
        self.dxva2_decoder = config.getboolean(section, "enable_dxva2_gpu_decode")
        self.pix_fmt = config.get(section, "pix-fmt").strip().lower()
        if self.pix_fmt == '':
            self.pix_fmt = None
        else:
            self.pix_fmt = self.pix_fmt.lower().replace(' ', '').split(',')

        self.awl = config.get(section, 'audio-language').strip().lower()  # List of acceptable languages for audio streams to be carried over from the original file, separated by a comma. Blank for all
        if self.awl == '':
            self.awl = None
        else:
            self.awl = self.awl.replace(' ', '').split(',')

        self.scodec = config.get(section, 'subtitle-codec').strip().lower()
        if not self.scodec or self.scodec == "":
            if self.embedsubs:
                self.scodec = ['mov_text']
            else:
                self.scodec = ['srt']
            self.log.warning("Invalid subtitle codec, defaulting to '%s'." % self.scodec)
        else:
            self.scodec = self.scodec.replace(' ', '').split(',')
        self.scodec_image = config.get(section, 'subtitle-codec-image-based').strip().lower()
        if not self.scodec_image or self.scodec_image == "":
            self.scodec_image = []
        else:
            self.scodec_image = self.scodec_image.replace(' ', '').split(',')

        self.swl = config.get(section, 'subtitle-language').strip().lower()  # List of acceptable languages for subtitle streams to be carried over from the original file, separated by a comma. Blank for all
        if self.swl == '':
            self.swl = None
        else:
            self.swl = self.swl.replace(' ', '').split(',')

        self.subencoding = config.get(section, 'subtitle-encoding').strip().lower()
        if self.subencoding == '':
            self.subencoding = None

        self.adl = config.get(section, 'audio-default-language').strip().lower()  # What language to default an undefinied audio language tag to. If blank, it will remain undefined. This is useful for single language releases which tend to leave things tagged as und
        if self.adl == "" or len(self.adl) > 3:
            self.adl = None

        self.sdl = config.get(section, 'subtitle-default-language').strip().lower()  # What language to default an undefinied subtitle language tag to. If blank, it will remain undefined. This is useful for single language releases which tend to leave things tagged as und
        if self.sdl == ""or len(self.sdl) > 3:
            self.sdl = None
        # Prevent incompatible combination of settings
        if self.output_dir == "" and self.delete is False:
            self.log.error("You must specify an alternate output directory if you aren't going to delete the original file.")
            sys.exit()
        # Create output directory if it does not exist
        if self.output_dir is not None:
            if not os.path.isdir(self.output_dir):
                os.makedirs(self.output_dir)
        self.process_same_extensions = config.getboolean(section, "process-same-extensions")  # Determine whether or not to reprocess mp4 files or just tag them
        self.forceConvert = config.getboolean(section, "force-convert")  # Force conversion even if everything is the same
        if self.forceConvert:
            self.process_same_extensions = True
            self.log.warning("Force-convert is true, so convert-mp4 is being overridden to true as well")
        self.fullpathguess = config.getboolean(section, "fullpathguess")  # Guess using the full path or not
        self.tagfile = config.getboolean(section, "tagfile")  # Tag files with metadata
        self.taglanguage = config.get(section, "tag-language").strip().lower()  # Language to tag files
        self.artwork = config.get(section, "download-artwork").lower()  # Download and embed artwork
        if self.artwork == "poster":
            self.artwork = True
            self.thumbnail = False
        elif self.artwork == "thumb" or self.artwork == "thumbnail":
            self.artwork = True
            self.thumbnail = True
        else:
            self.thumbnail = False
            try:
                self.artwork = config.getboolean(section, "download-artwork")
            except:
                self.artwork = True
                self.log.error("Invalid download-artwork value, defaulting to 'poster'.")

        self.preopts = config.get(section, "preopts")
        if self.preopts == '':
            self.preopts = None
        else:
            self.preopts = self.preopts.split(',')
            [o.strip() for o in self.preopts]

        self.postopts = config.get(section, "postopts")
        if self.postopts == '':
            self.postopts = None
        else:
            self.postopts = self.postopts.split(',')
            [o.strip() for o in self.postopts]

        # Read relevant CouchPotato section information
        section = "CouchPotato"
        self.CP = {}
        self.CP['host'] = config.get(section, "host")
        self.CP['port'] = config.get(section, "port")
        self.CP['username'] = config.get(section, "username")
        self.CP['password'] = config.get(section, "password")
        self.CP['apikey'] = config.get(section, "apikey")
        self.CP['delay'] = config.get(section, "delay")
        self.CP['method'] = config.get(section, "method")
        self.CP['web_root'] = config.get(section, "web_root")

        try:
            self.CP['delay'] = float(self.CP['delay'])
        except ValueError:
            self.CP['delay'] = 60
        try:
            self.CP['delete_failed'] = config.getboolean(section, "delete_failed")
        except (configparser.NoOptionError, ValueError):
            self.CP['delete_failed'] = False
        try:
            if config.getboolean(section, 'ssl'):
                self.CP['protocol'] = "https://"
            else:
                self.CP['protocol'] = "http://"
        except (configparser.NoOptionError, ValueError):
            self.CP['protocol'] = "http://"

        # Read relevant uTorrent section information
        section = "uTorrent"
        self.uTorrent = {}
        self.uTorrent['cp'] = config.get(section, "couchpotato-label").lower()
        self.uTorrent['sb'] = config.get(section, "sickbeard-label").lower()
        self.uTorrent['sr'] = config.get(section, "sickrage-label").lower()
        self.uTorrent['sonarr'] = config.get(section, "sonarr-label").lower()
        self.uTorrent['radarr'] = config.get(section, "radarr-label").lower()
        self.uTorrent['bypass'] = config.get(section, "bypass-label").lower()
        try:
            self.uTorrent['convert'] = config.getboolean(section, "convert")
        except:
            self.uTorrent['convert'] = False
        self.uTorrent['output_dir'] = config.get(section, "output_directory")
        if self.uTorrent['output_dir'] == '':
            self.uTorrent['output_dir'] = None
        else:
            self.uTorrent['output_dir'] = os.path.normpath(self.raw(self.uTorrent['output_dir']))  # Output directory
        self.uTorrentWebUI = config.getboolean(section, "webui")
        self.uTorrentActionBefore = config.get(section, "action_before").lower()
        self.uTorrentActionAfter = config.get(section, "action_after").lower()
        self.uTorrentHost = config.get(section, "host").lower()
        self.uTorrentUsername = config.get(section, "username")
        self.uTorrentPassword = config.get(section, "password")

        # Read relevant qBittorrent section information
        section = "qBittorrent"
        self.qBittorrent = {}
        self.qBittorrent['cp'] = config.get(section, "couchpotato-label").lower()
        self.qBittorrent['sb'] = config.get(section, "sickbeard-label").lower()
        self.qBittorrent['sr'] = config.get(section, "sickrage-label").lower()
        self.qBittorrent['sonarr'] = config.get(section, "sonarr-label").lower()
        self.qBittorrent['radarr'] = config.get(section, "radarr-label").lower()
        self.qBittorrent['bypass'] = config.get(section, "bypass-label").lower()
        try:
            self.qBittorrent['convert'] = config.getboolean(section, "convert")
        except:
            self.qBittorrent['convert'] = False
        self.qBittorrent['output_dir'] = config.get(section, "output_directory")
        if self.qBittorrent['output_dir'] == '':
            self.qBittorrent['output_dir'] = None
        else:
            self.qBittorrent['output_dir'] = os.path.normpath(self.raw(self.qBittorrent['output_dir']))  # Output directory
        self.qBittorrent['actionBefore'] = config.get(section, "action_before").lower()
        self.qBittorrent['actionAfter'] = config.get(section, "action_after").lower()
        self.qBittorrent['host'] = config.get(section, "host").lower()
        self.qBittorrent['username'] = config.get(section, "username")
        self.qBittorrent['password'] = config.get(section, "password")

        # Read relevant Deluge section information
        section = "Deluge"
        self.deluge = {}
        self.deluge['cp'] = config.get(section, "couchpotato-label").lower()
        self.deluge['sb'] = config.get(section, "sickbeard-label").lower()
        self.deluge['sr'] = config.get(section, "sickrage-label").lower()
        self.deluge['sonarr'] = config.get(section, "sonarr-label").lower()
        self.deluge['radarr'] = config.get(section, "radarr-label").lower()
        self.deluge['bypass'] = config.get(section, "bypass-label").lower()
        try:
            self.deluge['convert'] = config.getboolean(section, "convert")
        except:
            self.deluge['convert'] = False
        self.deluge['host'] = config.get(section, "host").lower()
        self.deluge['port'] = config.get(section, "port")
        self.deluge['user'] = config.get(section, "username")
        self.deluge['pass'] = config.get(section, "password")
        self.deluge['output_dir'] = config.get(section, "output_directory")
        self.deluge['remove'] = config.getboolean(section, "remove")
        if self.deluge['output_dir'] == '':
            self.deluge['output_dir'] = None
        else:
            self.deluge['output_dir'] = os.path.normpath(self.raw(self.deluge['output_dir']))  # Output directory

        # Read relevant Sonarr section information
        section = "Sonarr"
        self.Sonarr = {}
        self.Sonarr['host'] = config.get(section, "host")
        self.Sonarr['port'] = config.get(section, "port")
        self.Sonarr['apikey'] = config.get(section, "apikey")
        self.Sonarr['ssl'] = config.get(section, "ssl")
        self.Sonarr['web_root'] = config.get(section, "web_root")
        if not self.Sonarr['web_root'].startswith("/"):
            self.Sonarr['web_root'] = "/" + self.Sonarr['web_root']
        if self.Sonarr['web_root'].endswith("/"):
            self.Sonarr['web_root'] = self.Sonarr['web_root'][:-1]

        # Read relevant Radarr section information
        section = "Radarr"
        self.Radarr = {}
        self.Radarr['host'] = config.get(section, "host")
        self.Radarr['port'] = config.get(section, "port")
        self.Radarr['apikey'] = config.get(section, "apikey")
        self.Radarr['ssl'] = config.get(section, "ssl")
        self.Radarr['web_root'] = config.get(section, "web_root")
        if not self.Radarr['web_root'].startswith("/"):
            self.Radarr['web_root'] = "/" + self.Radarr['web_root']
        if self.Radarr['web_root'].endswith("/"):
            self.Radarr['web_root'] = self.Radarr['web_root'][:-1]

        # Read Sickbeard section information
        section = "SickBeard"
        self.Sickbeard = {}
        self.Sickbeard['host'] = config.get(section, "host")  # Server Address
        self.Sickbeard['port'] = config.get(section, "port")  # Server Port
        self.Sickbeard['api_key'] = config.get(section, "api_key")  # Sickbeard API key
        self.Sickbeard['web_root'] = config.get(section, "web_root")  # Sickbeard webroot
        self.Sickbeard['ssl'] = config.getboolean(section, "ssl")  # SSL
        self.Sickbeard['user'] = config.get(section, "username")
        self.Sickbeard['pass'] = config.get(section, "password")

        # Read Sickrage section information
        section = "Sickrage"
        self.Sickrage = {}
        self.Sickrage['host'] = config.get(section, "host")  # Server Address
        self.Sickrage['port'] = config.get(section, "port")  # Server Port
        self.Sickrage['api_key'] = config.get(section, "api_key")  # Sickbeard API key
        self.Sickrage['web_root'] = config.get(section, "web_root")  # Sickbeard webroot
        self.Sickrage['ssl'] = config.getboolean(section, "ssl")  # SSL
        self.Sickrage['user'] = config.get(section, "username")
        self.Sickrage['pass'] = config.get(section, "password")

        # Read SAB section information
        section = "SABNZBD"
        self.SAB = {}
        try:
            self.SAB['convert'] = config.getboolean(section, "convert")  # Convert
        except:
            self.SAB['convert'] = False
        self.SAB['cp'] = config.get(section, "Couchpotato-category").lower()
        self.SAB['sb'] = config.get(section, "Sickbeard-category").lower()
        self.SAB['sr'] = config.get(section, "Sickrage-category").lower()
        self.SAB['sonarr'] = config.get(section, "Sonarr-category").lower()
        self.SAB['radarr'] = config.get(section, "Radarr-category").lower()
        self.SAB['bypass'] = config.get(section, "Bypass-category").lower()
        self.SAB['output_dir'] = config.get(section, "output_directory")
        if self.SAB['output_dir'] == '':
            self.SAB['output_dir'] = None
        else:
            self.SAB['output_dir'] = os.path.normpath(self.raw(self.SAB['output_dir']))  # Output directory

        # Read Plex section information
        section = "Plex"
        self.Plex = {}
        self.Plex['host'] = config.get(section, "host")
        self.Plex['port'] = config.get(section, "port")
        try:
            self.Plex['refresh'] = config.getboolean(section, "refresh")
        except:
            self.Plex['refresh'] = False
        self.Plex['token'] = config.get(section, "token")
        if self.Plex['token'] == '':
            self.Plex['token'] = None

        # Pass the values on
        self.config = config
        self.configFile = configFile

        # Read Permissions section information
        section = "Permissions"
        self.permissions = {}
        self.permissions['chmod'] = config.get(section, 'chmod')
        try:
            self.permissions['chmod'] = int(self.permissions['chmod'], 8)
        except:
            self.log.exception("Invalid permissions, defaulting to 644.")
            self.permissions['chmod'] = int("0644", 8)
        self.permissions['uid'] = config.get(section, 'uid', vars=os.environ)
        self.permissions['gid'] = config.get(section, 'gid', vars=os.environ)
        try:
            self.permissions['uid'] = int(self.permissions['uid'])
        except:
            self.permissions['uid'] = -1
            self.log.exception("Invalid UID, defaulting to -1.")
        try:
            self.permissions['gid'] = int(self.permissions['gid'])
        except:
            self.permissions['gid'] = -1
            self.log.exception("Invalid GID, defaulting to -1.")

    def getRefreshURL(self, tvdb_id):
        config = self.config
        section = "SickBeard"

        protocol = "http://"  # SSL
        try:
            if config.getboolean(section, "ssl"):
                protocol = "https://"
        except (configparser.NoOptionError, ValueError):
            pass
        host = config.get(section, "host")  # Server Address
        port = config.get(section, "port")  # Server Port
        api_key = config.get(section, "api_key")  # Sickbeard API key
        web_root = config.get(section, "web_root")  # Sickbeard webroot

        sickbeard_url = protocol + host + ":" + port + web_root + "/api/" + api_key + "/?cmd=show.refresh&tvdbid=" + str(tvdb_id)
        return sickbeard_url

    def writeConfig(self, config, cfgfile):
        try:
            fp = open(cfgfile, "w")
            config.write(fp)
            fp.close()
        except IOError:
            self.log.exception("Error writing to autoProcess.ini.")
        except PermissionError:
            self.log.exception("Error writing to autoProcess.ini due to permissions.")

    def raw(self, text):
        escape_dict = {'\a': r'\a',
                       '\b': r'\b',
                       '\c': r'\c',
                       '\f': r'\f',
                       '\n': r'\n',
                       '\r': r'\r',
                       '\t': r'\t',
                       '\v': r'\v',
                       '\'': r'\'',
                       '\"': r'\"',
                       '\0': r'\0',
                       '\1': r'\1',
                       '\2': r'\2',
                       '\3': r'\3',
                       '\4': r'\4',
                       '\5': r'\5',
                       '\6': r'\6',
                       '\7': r'\7',
                       '\8': r'\8',
                       '\9': r'\9'}

        output = ''
        for char in text:
            try:
                output += escape_dict[char]
            except KeyError:
                output += char
        return output
