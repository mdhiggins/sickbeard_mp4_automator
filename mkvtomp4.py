import os
import sys
from converter import Converter

class MkvtoMp4:
    def __init__(self, file, FFMPEG_PATH="FFMPEG.exe", FFPROBE_PATH="FFPROBE.exe", delete=True, output_extension="mp4", output_dir=None):
        valid_input_extensions = ['mkv']
        valid_output_extensions = ['mp4', 'm4v']
        
        #Get path information from the input file
        working_dir, filename = os.path.split(file)
        filename, input_extension = os.path.splitext(filename)
        input_extension = input_extension[1:]
        
        #If no custom output directory is set, assume same directory as input file
        if output_dir is None:
            output_dir = working_dir
            
        if input_extension in valid_input_extensions and output_extension in valid_output_extensions:
            c = Converter(FFMPEG_PATH, FFPROBE_PATH)
            print "Reading " + file
            acodec = "aac"
            vcodec = "h264"
            info = c.probe(file)
            achannels = info.audio.audio_channels 
            print "Video codec detected: " + info.video.codec
            print "Audiocodec detected: " + info.audio.codec
            print "Channels detected: " + str(achannels)
            if info.video.codec == "h264" or info.videocodec == "x264":
                vcodec = "copy"
            if info.audio.codec == "aac":
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
            self.output = os.path.join(output_dir, filename + "." + output_extension)
            conv = c.convert(file, self.output, options)
            for timecode in conv:
                print '[{0}] {1}%'.format('#'*(timecode/10) + ' '*(10-(timecode/10)), timecode, end='\r')
            print "Conversion complete"
            if delete:
                try:
                    os.remove(file)
                    print file + " deleted"
                except OSError:
                    print "Unable to delete " + file
        elif input_extension in valid_output_extensions:
            self.output = file
        else:
            print file + " - file not in the correct format"
            sys.exit()