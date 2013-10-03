import os
import sys
import autoProcessTV
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")

path = str(sys.argv[1])
converter = MkvtoMp4(settings)
converter.output_dir = None
for r, d, f in os.walk(path):
    for files in f:
        inputfile = os.path.join(r, files)
        if converter.readSource(inputfile) is not False:
            converter.convert()

"""Contents of sabToSickbeard.py"""
if len(sys.argv) < 2:
    print "No folder supplied - is this being called from SABnzbd?"
    sys.exit()
elif len(sys.argv) >= 3:
    autoProcessTV.processEpisode(sys.argv[1], sys.argv[2])
else:
    autoProcessTV.processEpisode(sys.argv[1])
