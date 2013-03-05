import os
import sys
import ConfigParser


class ReadSettings:
    def __init__(self, directory, filename):
        sb_defaults = {'host': 'localhost',
                       'port': '8081',
                       'ssl': "False",
                       'api_key': '', }
        mp4_defaults = {'ffmpeg': 'ffmpeg.exe',
                        'ffprobe': 'ffprobe.exe',
                        'output_directory': '',
                        'output_extension': 'mp4',
                        'delete_original': 'True',
                        'relocate_moov': 'True',
                        'ios-audio': 'False',
                        'audio-language': '',
                        'subtitle-language': ''}
        defaults = sb_defaults.copy()
        defaults.update(mp4_defaults)
        section = "MP4"
        config = ConfigParser.SafeConfigParser()
        configFile = os.path.join(directory, filename)
        if os.path.isfile(configFile):
            fp = open(configFile, "rb")
            config.readfp(fp)
            fp.close()
        else:
            print "Error: Config file not found, using default values"
            config = ConfigParser.SafeConfigParser(defaults)

        if not config.has_section(section):
            config.add_section(section)

        changed = False
        for r in mp4_defaults:
            if not config.has_option(section, r):
                config.set(section, r, mp4_defaults[r])
                changed = True

        if changed:
            self.writeConfig(config, configFile)

        self.ffmpeg = config.get(section, "ffmpeg").replace("\\", "\\\\").replace("\\\\\\\\", "\\\\")  # Location of FFMPEG.exe
        self.ffprobe = config.get(section, "ffprobe").replace("\\", "\\\\").replace("\\\\\\\\", "\\\\")  # Location of FFPROBE.exe
        self.output_dir = config.get(section, "output_directory").replace("\\", "\\\\").replace("\\\\\\\\", "\\\\")  # Output directory
        self.output_extension = config.get(section, "output_extension")  # Output extension
        self.delete = config.getboolean(section, "delete_original")  # Delete original file
        self.relocate_moov = config.getboolean(section, "relocate_moov")  # Relocate MOOV atom to start of file
        self.iOS = config.getboolean(section, "ios-audio")  # Creates a second audio channel in AAC Stereo if the standard output methods are different from this for iOS compatability

        self.awl = config.get(section, 'audio-language')  # List of acceptable languages for audio streams to be carried over from the original file, separated by a comma. Blank for all
        if self.awl == '':
            self.awl = None
        else:
            self.awl = self.awl.split(',')
        self.swl = config.get(section, 'subtitle-language')  # List of acceptable languages for subtitle streams to be carried over from the original file, separated by a comma. Blank for all
        if self.swl == '':
            self.swl = None
        else:
            self.swl = self.swl.split(',')

        if self.output_dir == "" and self.delete is False:
            print "Error - you must specify an alternate output directory if you aren't going to delete the original file"
            sys.exit()

        if self.output_dir == "":
            self.output_dir = None
        else:
            if not os.path.isdir(self.output_dir):
                os.makedirs(self.output_dir)
        self.config = config
        self.configFile = configFile

    def getRefreshURL(self, tvdb_id):
        config = self.config
        section = "SickBeard"
        #SSL
        protocol = "http://"

        if not config.has_section(section):
            print "You need to put your sickbeard settings in the config file"
            sys.exit()

        if config.getboolean(section, "ssl"):
            protocol = "https://"
        host = config.get(section, "host")  # Server Address
        port = config.get(section, "port")  # Server Port
        if not config.has_option(section, "api_key"):
            config.set(section, "api_key", "")
            self.writeConfig(config, self.configFile)
        api_key = config.get(section, "api_key")  # Sickbeard API key

        sickbeard_url = protocol + host + ":" + port + "/api/" + api_key + "/?cmd=show.refresh&tvdbid=" + str(tvdb_id)
        return sickbeard_url

    def writeConfig(self, config, cfgfile):
            fp = open(cfgfile, "wb")
            try:
                config.write(fp)
            except IOError:
                pass
            fp.close()
