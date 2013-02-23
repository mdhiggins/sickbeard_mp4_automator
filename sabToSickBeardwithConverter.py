import os
import sys
import autoProcessTV
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4
from extensions import valid_input_extensions

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")

path = str(sys.argv[1])
for r, d, f in os.walk(path):
    for files in f:
        if os.path.splitext(files)[1][1:] in valid_input_extensions:
            file = os.path.join(r, files)
            convert = MkvtoMp4(file, settings.ffmpeg, settings.ffprobe, settings.delete, settings.output_extension)

"""Contents of sabToSickbeard.py"""
if len(sys.argv) < 2:
    print "No folder supplied - is this being called from SABnzbd?"
    sys.exit()
elif len(sys.argv) >= 3:
    autoProcessTV.processEpisode(sys.argv[1], sys.argv[2])
else:
    autoProcessTV.processEpisode(sys.argv[1])
