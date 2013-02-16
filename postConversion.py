import os
import sys
import json
import urllib
import ConfigParser
from tvdb_mp4 import Tvdb_mp4
from mkvtomp4 import MkvtoMp4

#Sickbeard API goodies
config = ConfigParser.ConfigParser()
configFile = os.path.join(os.path.dirname(sys.argv[0]),"tvdb_mp4.ini")
if not os.path.isfile(configFile):
    print "Error: Config file not found"
fp = open(configFile, "r")
config.readfp(fp)
fp.close()

ip = config.get("TVDB_MP4", "ip")
port = config.get("TVDB_MP4", "port")
api_key = config.get("TVDB_MP4", "api_key")
ffmpeg = config.get("TVDB_MP4", "ffmpeg").replace("\\","\\\\").replace("\\\\\\\\","\\\\")
ffprobe = config.get("TVDB_MP4", "ffprobe").replace("\\","\\\\").replace("\\\\\\\\","\\\\")
protocol = "http://"

if int(config.get("TVDB_MP4", "ssl")) == 1:
    protocol = "https://"

sickbeard_url = protocol + ip + ":" + port + "/api/" + api_key + "/"

if len(sys.argv) > 4:
    path = str(sys.argv[1]).replace("\\","\\\\").replace("\\\\\\\\","\\\\")
    tvdb_id = int(sys.argv[3])
    season = int(sys.argv[4])
    episode  = int(sys.argv[5])

    #Attempt to convert the file, if its already converted, say via sabToSickBeardwithConverter.py, it will just set the output file to the mp4
    if path.endswith(".mp4"):
        print "MP4 file detected, will not convert"
        finalpath = path
    else:
        print "Converting file " + path
        convert = MkvtoMp4(path, ffmpeg, ffprobe)
        fullURL = sickbeard_url+"?cmd=show.refresh&tvdbid=" + str(tvdb_id)
        refresh = json.load(urllib.urlopen(fullURL))
        for item in refresh:
            print refresh[item]
        finalpath = convert.output
        
    tagMp4 = Tvdb_mp4(tvdb_id, season, episode)
    tagMp4.writeTags(finalpath)
    
else:
    print "Not enough command line arguments present " + str(len(sys.argv))