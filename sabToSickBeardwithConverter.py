import os
import sys
import autoProcessTV
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")

path = str(sys.argv[1])
for r, d, f in os.walk(path):
    for files in f:
        file = os.path.join(r, files)
        convert = MkvtoMp4(file, FFMPEG_PATH=settings.ffmpeg, FFPROBE_PATH=settings.ffprobe, delete=settings.delete, output_extension=settings.output_extension, relocate_moov=settings.relocate_moov, iOS=settings.iOS, awl=settings.awl, swl=settings.swl, adl=settings.adl, sdl=settings.sdl, audio_codec=settings.acodec, processMP4=settings.processMP4)

"""Contents of sabToSickbeard.py"""
if len(sys.argv) < 2:
    print "No folder supplied - is this being called from SABnzbd?"
    sys.exit()
elif len(sys.argv) >= 3:
    autoProcessTV.processEpisode(sys.argv[1], sys.argv[2])
else:
    autoProcessTV.processEpisode(sys.argv[1])
