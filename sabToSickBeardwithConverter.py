import os
import sys
import autoProcessTV
import ConfigParser
from mkvtomp4 import MkvtoMp4
from converter import Converter
from extensions import valid_input_extensions

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
output_dir = config.get("TVDB_MP4", "output_directory").replace("\\","\\\\").replace("\\\\\\\\","\\\\")
output_extension = config.get("TVDB_MP4", "output_extension")
delete = config.getboolean("TVDB_MP4", "delete_original")

if output_dir == "" and delete is False:
    print "Error - you must specify an alternate output directory if you aren't going to delete the original file"
    sys.exit()

if output_dir == "":
    output_dir = None
else:
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

for r,d,f in os.walk(path):
    for files in f:
        if os.path.splitext(files)[1][1:] in valid_input_extensions:
            file = os.path.join(r,files)
            convert = MkvtoMp4(file, ffmpeg, ffprobe, delete, output_extension, output_dir)

"""Contents of sabToSickbeard.py"""                
if len(sys.argv) < 2:
    print "No folder supplied - is this being called from SABnzbd?"
    sys.exit()
elif len(sys.argv) >= 3:
    autoProcessTV.processEpisode(sys.argv[1], sys.argv[2])
else:
    autoProcessTV.processEpisode(sys.argv[1])