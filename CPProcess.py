#!/usr/bin/env python
import os
import sys
from readSettings import ReadSettings
from tmdb_mp4 import tmdb_mp4
from mkvtomp4 import MkvtoMp4


settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")

if len(sys.argv) > 2:
    inputfiles = sys.argv[3:]
    imdb_id = sys.argv[1]
    original = sys.argv[2]
    converter = MkvtoMp4(settings)

    for inputfile in inputfiles:
        if MkvtoMp4(settings).validSource(inputfile):
            output = converter.process(inputfile, original=original)
            
            # Tag with metadata
            if settings.tagfile:
                tagmp4 = tmdb_mp4(imdb_id, original=original)
                tagmp4.setHD(output['x'], output['y'])
                tagmp4.writeTags(output['output'])

            #QTFS
            if settings.relocate_moov:
                converter.QTFS(output['output'])

            # Copy to additional locations
            converter.replicate(output['output'])

else:
    print "Not enough command line arguments present " + str(len(sys.argv))
    sys.exit()
