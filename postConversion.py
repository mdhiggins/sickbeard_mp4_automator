#!/usr/bin/env python
import os
import sys
import json
import urllib
import shutil
from readSettings import ReadSettings
from tvdb_mp4 import Tvdb_mp4
from mkvtomp4 import MkvtoMp4
from extensions import valid_output_extensions
settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")

if len(sys.argv) > 4:
    path = sys.argv[1]
    extension = os.path.splitext(path)[1][1:]
    tvdb_id = int(sys.argv[3])
    season = int(sys.argv[4])
    episode = int(sys.argv[5])
    convert = MkvtoMp4(path, FFMPEG_PATH=settings.ffmpeg, FFPROBE_PATH=settings.ffprobe, delete=settings.delete, output_extension=settings.output_extension, relocate_moov=settings.relocate_moov, iOS=settings.iOS, awl=settings.awl, swl=settings.swl, adl=settings.adl, sdl=settings.sdl, audio_codec=settings.acodec, processMP4=settings.processMP4)
    if convert.output is not None:  #If output is not None it means the file should be a valid output file, proceed with attempts to tag
        tagmp4 = Tvdb_mp4(tvdb_id, season, episode)
        tagmp4.setHD(convert.width, convert.height)
        tagmp4.writeTags(convert.output)

        if settings.relocate_moov:
            convert.QTFS()

        try:
            refresh = json.load(urllib.urlopen(settings.getRefreshURL(tvdb_id)))
            for item in refresh:
                print refresh[item]
        except IOError:
            print "Couldn't refresh Sickbeard, check your settings"

        if settings.output_dir is not None:
            output = os.path.join(settings.output_dir, os.path.split(convert.output)[1])
            if extension in valid_output_extensions and settings.delete is False and settings.processMP4 is False:  # If the file is already in a valid format, this will duplicate the file in the output directory since no original would be left behind
                try:
                    shutil.copy(convert.output, output)
                    print "Copied %s to %s" % (convert.output, output)
                except (OSError, IOError) as e:
                    print "Unable to copy %s to %s: %s" % (convert.output, output, e.strerror)
            else:  # Otherwise just move the file like normal, leaving behind the original MKV
                try:
                    shutil.move(convert.output, output)
                    print "Moved %s to %s" % (convert.output, output)
                except (OSError, IOError) as e:
                    print "Unable to move %s to %s: %s" % (convert.output, output, e.strerror)
else:
    print "Not enough command line arguments present " + str(len(sys.argv))
    sys.exit()
