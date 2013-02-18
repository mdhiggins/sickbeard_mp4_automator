import os
import sys
import json
import urllib
from readSettings import ReadSettings
from tvdb_mp4 import Tvdb_mp4
from mkvtomp4 import MkvtoMp4
from extensions import valid_output_extensions

settings = ReadSettings(os.path.dirname(sys.argv[0]), "tvdb_mp4.ini")

if len(sys.argv) > 4:
    path = str(sys.argv[1]).replace("\\","\\\\").replace("\\\\\\\\","\\\\")
    extension = os.path.splitext(path)[1][1:]
    tvdb_id = int(sys.argv[3])
    season = int(sys.argv[4])
    episode  = int(sys.argv[5])

    convert = MkvtoMp4(path, settings.ffmpeg, settings.ffprobe, settings.delete, settings.output_extension, settings.output_dir)
    if extension not in valid_output_extensions:
        path = convert.output
        try:
            refresh = json.load(urllib.urlopen(settings.getRefreshURL(tvdb_id)))
            for item in refresh:
                print refresh[item]
        except IOError:
            print "Couldn't refresh Sickbeard, check your tvdb_mp4.ini settings"
    tagmp4 = Tvdb_mp4(tvdb_id, season, episode)
    tagmp4.setHD(convert.width, convert.height)
    tagmp4.writeTags(path)
    if (settings.move_dir is not None):
        output_dir, filename = os.path.split(convert.output)
        final_dest = os.path.join(settings.move_dir, filename)
        os.rename(convert.output, final_dest)
        print "Moving file to " + str(final_dest)
else:
    print "Not enough command line arguments present " + str(len(sys.argv))
    sys.exit()
