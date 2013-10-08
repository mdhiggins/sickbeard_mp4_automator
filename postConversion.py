#!/usr/bin/env python
import os
import sys
import json
import urllib
from readSettings import ReadSettings
from tvdb_mp4 import Tvdb_mp4
from mkvtomp4 import MkvtoMp4
settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")

if len(sys.argv) > 4:
    inputfile = sys.argv[1]
    tvdb_id = int(sys.argv[3])
    season = int(sys.argv[4])
    episode = int(sys.argv[5])
    converter = MkvtoMp4(settings)
    
    if MkvtoMp4(settings).validSource(inputfile):
        output = converter.process(inputfile)
        
        # Tag with metadata
        if settings.tagfile:
            tagmp4 = Tvdb_mp4(tvdb_id, season, episode)
            tagmp4.setHD(output['x'], output['y'])
            tagmp4.writeTags(output['output'])

            #QTFS (only if file is tagged)
            if settings.relocate_moov:
                converter.QTFS(output['output'])

        # Copy to additional locations
        if settings.copyto:
            converter.replicate(output['output'])

        try:
            refresh = json.load(urllib.urlopen(settings.getRefreshURL(tvdb_id)))
            for item in refresh:
                print refresh[item]
        except IOError:
            print "Couldn't refresh Sickbeard, check your settings"

else:
    print "Not enough command line arguments present " + str(len(sys.argv))
    sys.exit()
