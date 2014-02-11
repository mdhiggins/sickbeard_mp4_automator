#!/usr/bin/env python

import os
import sys
import autoProcessMovie
from tmdb_api import tmdb
from tmdb_mp4 import tmdb_mp4
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4
from extensions import tmdb_api_key

print "nzbToCouchPotato MP4 edition"


if len(sys.argv) > 3:
    settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
    converter = MkvtoMp4(settings)
    path = str(sys.argv[1])
    moviefile = None
    maxsize = 0
    for r, d, f in os.walk(path):
        for files in f:
            inputfile = os.path.join(r, files)
            
            if MkvtoMp4(settings).validSource(inputfile):
                converter.process(moviefile)


# SABnzbd
if len(sys.argv) == 8:
# SABnzbd argv:
# 1 The final directory of the job (full path)
# 2 The original name of the NZB file
# 3 Clean version of the job name (no path info and ".nzb" removed)
# 4 Indexer's report number (if supported)
# 5 User-defined category
# 6 Group that the NZB was posted in e.g. alt.binaries.x
# 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    print "Script triggered from SABnzbd, starting autoProcessMovie..."
    autoProcessMovie.process(sys.argv[1], sys.argv[2], sys.argv[7])

# NZBGet
elif len(sys.argv) == 4:
# NZBGet argv:
# 1  The final directory of the job (full path)
# 2  The original name of the NZB file
# 3  The status of the download: 0 == successful
    print "Script triggered from NZBGet, starting autoProcessMovie..."
    autoProcessMovie.process(sys.argv[1], sys.argv[2], sys.argv[3])

else:
    print "Invalid number of arguments received from client."
    print "Running autoProcessMovie as a manual run..."
    autoProcessMovie.process('Manual Run', 'Manual Run', 0)
