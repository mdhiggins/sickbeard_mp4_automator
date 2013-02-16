import os
import sys
import json
import urllib
import ConfigParser
from tvdb_mp4 import Tvdb_mp4
from mkvtomp4 import MkvtoMp4
from extensions import valid_output_extensions

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
output_dir = config.get("TVDB_MP4", "output_directory").replace("\\","\\\\").replace("\\\\\\\\","\\\\")
output_extension = config.get("TVDB_MP4", "output_extension")
delete = config.getboolean("TVDB_MP4", "delete_original")
protocol = "http://"

if config.getboolean("TVDB_MP4", "ssl"):
    protocol = "https://"

if output_dir == "" and delete is False:
    print "Error - you must specific an alternate output directory if you aren't going to delete the original file"
    sys.exit()
    
sickbeard_url = protocol + ip + ":" + port + "/api/" + api_key + "/"

if len(sys.argv) > 4:
    path = str(sys.argv[1]).replace("\\","\\\\").replace("\\\\\\\\","\\\\")
    extension = os.path.splitext(path)[1][1:]
    tvdb_id = int(sys.argv[3])
    season = int(sys.argv[4])
    episode  = int(sys.argv[5])

    if extension not in valid_output_extensions:
        convert = MkvtoMp4(path, ffmpeg, ffprobe)
        path = convert.output
        fullURL = sickbeard_url + "?cmd=show.refresh&tvdbid=" + str(tvdb_id)
        refresh = json.load(urllib.urlopen(fullURL))
        for item in refresh:
            print refresh[item]
        
    tagmp4 = Tvdb_mp4(tvdb_id, season, episode)
    tagmp4.writeTags(path)
else:
    print "Not enough command line arguments present " + str(len(sys.argv))
    sys.exit()