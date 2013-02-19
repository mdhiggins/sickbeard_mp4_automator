import os
import sys
import ConfigParser

class ReadSettings:
    def __init__ (self, directory, filename):
        defaults = {'ip': 'localhost',
                    'port': '8081',
                    'ssl': "False",
                    'api_key': '',
                    'ffmpeg': 'ffmpeg.exe',
                    'ffprobe': 'ffprobe.exe',
                    'output_directory': '',
                    'output_extension': 'mp4',
                    'delete_original': "True"}
        self.section = "TVDB_MP4"
        config = ConfigParser.SafeConfigParser(defaults)
        configFile = os.path.join(directory, filename)
        if os.path.isfile(configFile):
            fp = open(configFile, "r")
            config.readfp(fp)
            fp.close()
        else:
            print "Error: Config file not found, using default values"
        if not config.has_section(self.section):
            self.section = "DEFAULT"
        self.ffmpeg = config.get(self.section, "ffmpeg").replace("\\","\\\\").replace("\\\\\\\\","\\\\") #Location of FFMPEG.exe
        self.ffprobe = config.get(self.section, "ffprobe").replace("\\","\\\\").replace("\\\\\\\\","\\\\") #Location of FFPROBE.exe
        self.output_dir = config.get(self.section, "output_directory").replace("\\","\\\\").replace("\\\\\\\\","\\\\") #Output directory
        self.output_extension = config.get(self.section, "output_extension") #Output extension
        self.delete = config.getboolean(self.section, "delete_original") #Delete original file

        if self.output_dir == "" and self.delete is False:
            print "Error - you must specify an alternate output directory if you aren't going to delete the original file"
            sys.exit()

        if self.output_dir == "":
            self.output_dir = None
        else:
            if not os.path.isdir(self.output_dir):
                os.makedirs(self.output_dir)
        self.config = config
    def getRefreshURL (self, tvdb_id):
        config = self.config
        #SSL
        protocol = "http://"
        if config.getboolean(self.section, "ssl"):
            protocol = "https://"
        ip = config.get(self.section, "ip") #Server Address
        port = config.get(self.section, "port") #Server Port
        api_key = config.get(self.section, "api_key") #Sickbeard API key
        sickbeard_url = protocol + ip + ":" + port + "/api/" + api_key + "/?cmd=show.refresh&tvdbid=" + str(tvdb_id)
        return sickbeard_url