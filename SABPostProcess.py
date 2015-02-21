#!/usr/bin/env python

import os
import sys
import autoProcessTV, autoProcessMovie
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4

# SABnzbd argv:
# 1 The final directory of the job (full path)
# 2 The original name of the NZB file
# 3 Clean version of the job name (no path info and ".nzb" removed)
# 4 Indexer's report number (if supported)
# 5 User-defined category
# 6 Group that the NZB was posted in e.g. alt.binaries.x
# 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
categories = ['sickbeard', 'couchpotato']
category = str(sys.argv[5])

if category.lower() not in categories:
    print "Error, no valid category detected"

path = str(sys.argv[1])
nzb = str(sys.argv[2])

if settings.Sickbeard['convert']:
    print "Converting before passing"
    converter = MkvtoMp4(settings)
    converter.output_dir = None
    for r, d, f in os.walk(path):
        for files in f:
            inputfile = os.path.join(r, files)
            if MkvtoMp4(settings).validSource(inputfile):
                try:
                	print "Valid file detected: " + inputfile
                except:
                	print "Valid file detected"
                converter.process(inputfile)
else:
    print "Passing without conversion"

# Send to Sickbeard
if category.lower() == categories[0]:
    if len(sys.argv) < 2:
        print "No folder supplied - is this being called from SABnzbd?"
        sys.exit()
    elif len(sys.argv) >= 3:
        autoProcessTV.processEpisode(path, nzb)
    else:
        autoProcessTV.processEpisode(path)

# Send to CouchPotato        
elif category.lower() == categories[1]:
    autoProcessMovie.process(sys.argv[1], sys.argv[2], sys.argv[7])