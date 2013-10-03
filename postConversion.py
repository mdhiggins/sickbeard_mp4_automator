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
    path = sys.argv[1]
    tvdb_id = int(sys.argv[3])
    season = int(sys.argv[4])
    episode = int(sys.argv[5])
    converter = MkvtoMp4(settings)
    if converter.readSource(path) is not False:
        output = converter.convert()
        tagmp4 = Tvdb_mp4(tvdb_id, season, episode)
        tagmp4.setHD(output['width'], output['height'])
        tagmp4.writeTags(output['file'])

        if settings.relocate_moov:
            converter.QTFS()

        if settings.local and settings.output_dir is not None:
            converter.move()

        try:
            refresh = json.load(urllib.urlopen(settings.getRefreshURL(tvdb_id)))
            for item in refresh:
                print refresh[item]
        except IOError:
            print "Couldn't refresh Sickbeard, check your settings"

else:
    print "Not enough command line arguments present " + str(len(sys.argv))
    sys.exit()
