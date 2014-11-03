import os
import sys
import ConfigParser
from extensions import *
from babelfish import Language
try:
    from babelfish import Language
except:
    print "Trying to install SetupTools"
    try:
        import setup
        setup.ez_setup.main()
        from babelfish import Language
    except:
        print "Please install SetupTools"


class ReadSettings:

    def __init__(self, directory, filename):
        # Default settings for SickBeard
        sb_defaults = {'host': 'localhost',
                       'port': '8081',
                       'ssl': "False",
                       'api_key': '', }
       # Default MP4 conversion settings
        mp4_defaults = {'ffmpeg': 'ffmpeg.exe',
                        'ffprobe': 'ffprobe.exe',
                        'output_directory': '',
                        'copy_to': '',
                        'move_to': '',
                        'output_extension': 'mp4',
                        'output_format': 'mp4',
                        'delete_original': 'True',
                        'relocate_moov': 'True',
                        'ios-audio': 'True',
                        'max-audio-channels': '',
                        'audio-language': '',
                        'audio-codec': 'ac3',
                        'audio-channel-bitrate': '256',
                        'video-codec': 'h264, x264',
                        'subtitle-language': '',
                        'audio-default-language': '',
                        'subtitle-default-language': '',
                        'convert-mp4': 'False',
                        'fullpathguess': 'True',
                        'tagfile': 'True',
                        'tag-language': 'en',
                        'download-artwork': 'True',
                        'download-subs': 'False',
                        'embed-subs': 'True',
                        'sub-providers': 'addic7ed, podnapisi, thesubdb, opensubtitles' }
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
        # Default uTorrent settings
        utorrent_defaults = { 'label': '' }

        defaults = {'SickBeard': sb_defaults, 'CouchPotato': cp_defaults, 'MP4': mp4_defaults, 'uTorrent': utorrent_defaults}
        write = False  # Will be changed to true if a value is missing from the config file and needs to be written

        config = ConfigParser.SafeConfigParser()
        configFile = os.path.join(directory, filename)
        if os.path.isfile(configFile):
            fp = open(configFile, "rb")
            config.readfp(fp)
            fp.close()
        else:
            print "Error: Config file not found, creating"
            #config.filename = filename
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

        #Read relevant MP4 section information
        section = "MP4"
        self.ffmpeg = os.path.normpath(self.raw(config.get(section, "ffmpeg")))  # Location of FFMPEG.exe
        self.ffprobe = os.path.normpath(self.raw(config.get(section, "ffprobe")))  # Location of FFPROBE.exe
        self.output_dir = config.get(section, "output_directory")
        if self.output_dir == '':
            self.output_dir = None
        else:
            self.output_dir = os.path.normpath(self.raw(self.output_dir))  # Output directory
        self.copyto = config.get(section, "copy_to") # Directories to make copies of the final product
        if self.copyto == '':
            self.copyto = None
        else:
            self.copyto = self.copyto.split('|')
            for i in xrange(len(self.copyto)):
                self.copyto[i] = os.path.normpath(self.copyto[i])
                if not os.path.isdir(self.copyto[i]):
                    try:
                        os.makedirs(self.copyto[i])
                    except:
                        print "Error making directory %s" % (self.copyto[i])
        self.moveto = config.get(section, "move_to") # Directory to move final product to
        if self.moveto == '':
            self.moveto = None
        else:
            self.moveto = os.path.normpath(self.moveto)
            if not os.path.isdir(self.moveto):
                try:
                    os.makedirs(self.moveto)
                except:
                    print "Error making directory %s" % (self.moveto)
                    self.moveto = None

        self.output_extension = config.get(section, "output_extension")  # Output extension
        self.output_format = config.get(section, "output_format") # Output format
        if self.output_format not in valid_formats:
            self.output_format = 'mov'
        self.delete = config.getboolean(section, "delete_original")  # Delete original file
        self.relocate_moov = config.getboolean(section, "relocate_moov")  # Relocate MOOV atom to start of file
        self.acodec = config.get(section, "audio-codec").lower()  # Gets the desired audio codec, if no valid codec selected, default to AC3
        if self.acodec == '':
            self.acodec == ['ac3']
        else:
            self.acodec = self.acodec.lower().replace(' ', '').split(',')

        self.abitrate = config.get(section, "audio-channel-bitrate")
        try:
            self.abitrate = int(self.abitrate)
        except:
            self.abitrate = 256
            print "Audio bitrate was invalid, defaulting to 256 per channel"
        if self.abitrate > 256:
            print "Warning - audio bitrates >256 may create errors with common codecs"

        # !!! Leaving this disabled for now, users will be responsible for knowing whicn codecs do and don't work with mp4 files !!!
        #if self.acodec not in valid_audio_codecs:
        #    self.acodec = 'aac'
        #    print "Audio codec not valid, defaulting to AAC"
        
        self.iOS = config.get(section, "ios-audio")  # Creates a second audio channel if the standard output methods are different from this for iOS compatability
        if self.iOS == "" or self.iOS.lower() in ['false', 'no', 'f', '0']:
            self.iOS = False
        else:
            if self.iOS.lower() in ['true', 'yes', 't', '1']:
                self.iOS = 'aac'
        self.downloadsubs = config.getboolean(section, "download-subs")  # Enables downloading of subtitles from the internet sources using subliminal

        if self.downloadsubs:
            try:
                import subliminal
            except Exception as e:
                print e
                self.downloadsubs = False
                print "Subliminal is not installed, automatically downloading of subs has been disabled"
        self.subproviders = config.get(section, 'sub-providers').lower()
        if self.subproviders == '':
            self.downloadsubs = False
            print "You must specifiy at least one subtitle provider to downlaod subs automatically"
        else:
            self.subproviders = self.subproviders.lower().replace(' ', '').split(',')

        self.embedsubs = config.getboolean(section, 'embed-subs')

        #Setup variable for maximum audio channels
        self.maxchannels = config.get(section, 'max-audio-channels')
        if self.maxchannels == "":
            self.maxchannels = None
        else:
            try:
                self.maxchannels = int(self.maxchannels)
            except:
                print "Invalid number of audio channels specified"
                self.maxchannels = None
        if self.maxchannels is not None and self.maxchannels < 1:
            print "Must have at least 1 audio channel"
            self.maxchannels = None

        self.vcodec = config.get(section, "video-codec")
        if self.vcodec == '':
            self.vcodec == ['h264', 'x264']
        else:
            self.vcodec = self.vcodec.lower().replace(' ', '').split(',')

        self.awl = config.get(section, 'audio-language').strip().lower()  # List of acceptable languages for audio streams to be carried over from the original file, separated by a comma. Blank for all
        if self.awl == '':
            self.awl = None
        else:
            self.awl = self.awl.replace(' ', '').split(',')

        self.swl = config.get(section, 'subtitle-language').strip().lower()  # List of acceptable languages for subtitle streams to be carried over from the original file, separated by a comma. Blank for all
        if self.swl == '':
            self.swl = None
        else:
            self.swl = self.swl.replace(' ', '').split(',')

        self.adl = config.get(section, 'audio-default-language').strip().lower()  # What language to default an undefinied audio language tag to. If blank, it will remain undefined. This is useful for single language releases which tend to leave things tagged as und
        if self.adl == "" or len(self.adl) > 3:
            self.adl = None

        self.sdl = config.get(section, 'subtitle-default-language').strip().lower()  # What language to default an undefinied subtitle language tag to. If blank, it will remain undefined. This is useful for single language releases which tend to leave things tagged as und
        if self.sdl == ""or len(self.sdl) > 3:
            self.sdl = None
        # Prevent incompatible combination of settings
        if self.output_dir == "" and self.delete is False:
            print "Error - you must specify an alternate output directory if you aren't going to delete the original file"
            sys.exit()
        # Create output directory if it does not exist
        if self.output_dir is not None:
            if not os.path.isdir(self.output_dir):
                os.makedirs(self.output_dir)
        self.processMP4 = config.getboolean(section, "convert-mp4")  # Determine whether or not to reprocess mp4 files or just tag them
        self.fullpathguess = config.getboolean(section, "fullpathguess") # Guess using the full path or not
        self.tagfile = config.getboolean(section, "tagfile") # Tag files with metadata
        self.taglanguage = config.get(section, "tag-language").strip().lower() # Language to tag files
        if len(self.taglanguage) > 2:
            try:
                babel = Language.fromalpha3(self.taglanguage)
                self.taglanguage = babel.alpha2
            except:
                print "Unable to set tag language, defaulting to English"
                self.taglanguage = 'en'
        elif len(self.taglanguage) < 2:
            print "Unable to set tag language, defaulting to English"
            self.taglanguage = 'en'
        self.artwork = config.getboolean(section, "download-artwork") # Download and embed artwork

        #Read relevant CouchPotato section information
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
        except (ConfigParser.NoOptionError, ValueError):
            self.CP['delete_failed'] = False
        try:
            if config.getboolean(section, 'ssl'):
                self.CP['protocol'] = "https://"
            else:
                self.CP['protocol'] = "http://"
        except (ConfigParser.NoOptionError, ValueError):
            self.CP['protocol'] = "http://"

        #Read relevant uTorrent section information
        section = "uTorrent"
        self.uTorrentLabel = config.get(section, "label").lower()
        if self.uTorrentLabel == "":
            self.uTorrentLabel = None;

        #Pass the values on
        self.config = config
        self.configFile = configFile

    def getRefreshURL(self, tvdb_id):
        config = self.config
        section = "SickBeard"

        protocol = "http://"  # SSL
        try:
            if config.getboolean(section, "ssl"):
                protocol = "https://"
        except (ConfigParser.NoOptionError, ValueError):
            pass
        host = config.get(section, "host")  # Server Address
        port = config.get(section, "port")  # Server Port
        api_key = config.get(section, "api_key")  # Sickbeard API key
        web_root = config.get(section, "web_root")  # Sickbeard webroot

        sickbeard_url = protocol + host + ":" + port + web_root +"/api/" + api_key + "/?cmd=show.refresh&tvdbid=" + str(tvdb_id)
        return sickbeard_url

    def writeConfig(self, config, cfgfile):
            fp = open(cfgfile, "wb")
            try:
                config.write(fp)
            except IOError:
                pass
            fp.close()

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
