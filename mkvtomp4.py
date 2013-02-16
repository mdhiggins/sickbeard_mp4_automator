import os
import sys
from converter import Converter

class MkvtoMp4:
    def __init__(self, file, FFMPEG_PATH, FFPROBE_PATH):
        c = Converter(FFMPEG_PATH, FFPROBE_PATH)
        if file.endswith(".mkv"):
            print "Reading " + file
            acodec = "aac"
            vcodec = "h264"
            info = c.probe(file)
            achannels = info.audio.audio_channels 
            print "Video codec detected: " + info.video.codec
            print "Audiocodec detected: " + info.audio.codec
            print "Channels detected: " + str(achannels)
            if info.video.codec == "h264" or info.videocodec == "x264":
                print "Video is in the correct format"
                vcodec = "copy"
            if info.audio.codec == "aac":
                print "Audio is in the correct format"
                acodec == "copy"
            options = {
                        'format': 'mp4',
                        'audio': {
                            'codec': acodec,
                            'channels': achannels,
                            'bitrate': 448,
                            'language': "eng",
                        },
                        'video': {
                            'codec': vcodec,
                        },
                    }
            self.output = file[:-4] + ".mp4"
            conv = c.convert(file, self.output, options)
            for timecode in conv:
                print '[{0}] {1}%'.format('#'*(timecode/10) + ' '*(10-(timecode/10)), timecode, end='\r')
            print "Conversion complete"
            try:
                os.remove(file)
                print file + " deleted"
            except OSError:
                print "Unable to delete " + file
        elif file.endswith(".mp4"):
            self.output = file
        else:
            print file + " - file cannot be converted and is not an mp4"
            sys.exit()