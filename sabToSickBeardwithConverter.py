import os
import sys
import autoProcessTV
import ConfigParser
from mkvtomp4 import MkvtoMp4
from converter import Converter

path = str(sys.argv[1])

config = ConfigParser.ConfigParser()
configFile = os.path.join(os.path.dirname(sys.argv[0]),"tvdb_mp4.ini")
if not os.path.isfile(configFile):
    print "Error: Config file not found"
    sys.exit()
fp = open(configFile, "r")
config.readfp(fp)
fp.close()

ffmpeg = config.get("TVDB_MP4", "ffmpeg").replace("\\","\\\\").replace("\\\\\\\\","\\\\")
ffprobe = config.get("TVDB_MP4", "ffprobe").replace("\\","\\\\").replace("\\\\\\\\","\\\\")

for r,d,f in os.walk(path):
    for files in f:
        if files.endswith(".mkv"):
            file = os.path.join(r,files)
            convert = MkvtoMp4(file, ffmpeg, ffprobe)

"""Contents of sabToSickbeard.py"""                
if len(sys.argv) < 2:
    print "No folder supplied - is this being called from SABnzbd?"
    sys.exit()
elif len(sys.argv) >= 3:
    autoProcessTV.processEpisode(sys.argv[1], sys.argv[2])
else:
    autoProcessTV.processEpisode(sys.argv[1])