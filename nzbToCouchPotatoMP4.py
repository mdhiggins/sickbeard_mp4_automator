#!/usr/bin/env python
import os
import sys
import autoProcessMovie
from imdb_mp4 import imdb_mp4
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4
from extensions import valid_input_extensions

print "nzbToCouchPotato MP4 edition"


def NZBtoIMDB(nzbName):
    nzbName = str(nzbName)
    a = nzbName.find('.cp(tt') + 6
    b = nzbName[a:].find(')') + a
    imdbid = nzbName[a:b]
    return imdbid

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
imdb_id = NZBtoIMDB(sys.argv[2])

if len(sys.argv) > 3:
    path = str(sys.argv[1])
    for r, d, f in os.walk(path):
        for files in f:
            if os.path.splitext(files)[1][1:] in valid_input_extensions:
                file = os.path.join(r, files)
                convert = MkvtoMp4(file, FFMPEG_PATH=settings.ffmpeg, FFPROBE_PATH=settings.ffprobe, delete=settings.delete, output_extension=settings.output_extension, relocate_moov=settings.relocate_moov, iOS=settings.iOS, awl=settings.awl, swl=settings.swl)
                imdbmp4 = imdb_mp4(imdb_id)
                imdbmp4.setHD(convert.width, convert.height)
                imdbmp4.writeTags(convert.output)

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
