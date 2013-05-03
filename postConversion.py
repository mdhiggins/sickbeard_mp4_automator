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
    path = str(sys.argv[1]).replace("\\", "\\\\").replace("\\\\\\\\", "\\\\")
    extension = os.path.splitext(path)[1][1:]
    tvdb_id = int(sys.argv[3])
    season = int(sys.argv[4])
    episode = int(sys.argv[5])
    convert = MkvtoMp4(path, FFMPEG_PATH=settings.ffmpeg, FFPROBE_PATH=settings.ffprobe, delete=settings.delete, output_extension=settings.output_extension, relocate_moov=settings.relocate_moov, iOS=settings.iOS, awl=settings.awl, swl=settings.swl, adl=settings.adl, sdl=settings.sdl, audio_codec=settings.acodec)
    if extension not in valid_output_extensions:
        path = convert.output
        try:
            refresh = json.load(urllib.urlopen(settings.getRefreshURL(tvdb_id)))
            for item in refresh:
                print refresh[item]
        except IOError:
            print "Couldn't refresh Sickbeard, check your settings"
    tagmp4 = Tvdb_mp4(tvdb_id, season, episode)
    tagmp4.setHD(convert.width, convert.height)
    tagmp4.writeTags(path)
    if settings.output_dir is not None:
        if extension in valid_output_extensions and settings.delete is False:  # If the file is already in a valid format, this will duplicate the file in the output directory since no original would be left behind
            output = os.path.join(settings.output_dir, os.path.split(path)[1])
            try:
                shutil.copy(path, output)
            except (OSError, IOError) as e:
                print "Unable to copy %s to %s: %s" % (path, output, e.strerror)
        else:  # Otherwise just move the file like normal, leaving behind the original MKV
            try:
                shutil.move(path, output)
            except (OSError, IOError) as e:
                print "Unable to move %s to %s: %s" % (path, output, e.strerror)
else:
    print "Not enough command line arguments present " + str(len(sys.argv))
    sys.exit()
