#!/usr/bin/env python
 
import os
import sys
import autoProcessMovie
import nzbDroneFactory
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4
 
print "nzbToNzbDrone MP4 edition"
 
if len(sys.argv) > 3:
    settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
    converter = MkvtoMp4(settings)
    path = str(sys.argv[1])
    for r, d, f in os.walk(path):
        for files in f:
            inputfile = os.path.join(r, files)
            if MkvtoMp4(settings).validSource(inputfile):
                print "Processing episode " + inputfile
                converter.process(inputfile)
 
 
#NzbDrone
# SABnzbd
if len(sys.argv) ==8:
# SABnzbd argv:
# 1 The final directory of the job (full path)
# 2 The original name of the NZB file
# 3 Clean version of the job name (no path info and ".nzb" removed)
# 4 Indexer's report number (if supported)
# 5 User-defined category
# 6 Group that the NZB was posted in e.g. alt.binaries.x
# 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    print "Script triggered from SABnzbd, starting nzbDroneFactory..."
    nzbDroneFactory.scan(sys.argv[1], sys.argv[7])
 
# NZBGet
elif len(sys.argv) == 4:
# NZBGet argv:
# 1  The final directory of the job (full path)
# 2  The original name of the NZB file
# 3  The status of the download: 0 == successful
    print "Script triggered from NZBGet, starting nzbDroneFactory..."
    nzbDroneFactory.scan(sys.argv[1], sys.argv[3])
 
else:
    print "Invalid number of arguments received from client."
    print "Running autoProcessMovie as a manual run..."
    autoProcessMovie.process('Manual Run', 'Manual Run', 0)
