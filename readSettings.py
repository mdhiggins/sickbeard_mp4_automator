import os
import sys
import ConfigParser

class ReadSettings:
    def __init__ (self, directory, filename):
        config = ConfigParser.ConfigParser()
        configFile = os.path.join(directory, filename)
        if not os.path.isfile(configFile):
            print "Error: Config file not found"
            sys.exit()
        fp = open(configFile, "r")
        config.readfp(fp)
        fp.close()


        self.ip = config.get("TVDB_MP4", "ip") #Server Address
        self.port = config.get("TVDB_MP4", "port") #Server Port
        self.api_key = config.get("TVDB_MP4", "api_key") #Sickbeard API key
        self.ffmpeg = config.get("TVDB_MP4", "ffmpeg").replace("\\","\\\\").replace("\\\\\\\\","\\\\") #Location of FFMPEG.exe
        self.ffprobe = config.get("TVDB_MP4", "ffprobe").replace("\\","\\\\").replace("\\\\\\\\","\\\\") #Location of FFPROBE.exe
        self.output_dir = config.get("TVDB_MP4", "output_directory").replace("\\","\\\\").replace("\\\\\\\\","\\\\") #Output directory
        self.output_extension = config.get("TVDB_MP4", "output_extension") #Output extension
        self.delete = config.getboolean("TVDB_MP4", "delete_original") #Delete original file
        self.move_dir = config.get("TVDB_MP4", "move_directory").replace("\\","\\\\").replace("\\\\\\\\","\\\\") #Move directory

        #SSL
        self.protocol = "http://"
        if config.getboolean("TVDB_MP4", "ssl"):
            self.protocol = "https://"

        if self.output_dir == "" and self.delete is False:
            print "Error - you must specify an alternate output directory if you aren't going to delete the original file"
            sys.exit()

        if self.output_dir == "":
            self.output_dir = None
        else:
            if not os.path.isdir(self.output_dir):
                os.makedirs(self.output_dir)

    def getRefreshURL (self, tvdb_id):
        sickbeard_url = self.protocol + self.ip + ":" + self.port + "/api/" + self.api_key + "/?cmd=show.refresh&tvdbid=" + str(tvdb_id)
        return sickbeard_url
