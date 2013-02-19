import os
import sys
from converter import Converter
from extensions import valid_input_extensions, valid_output_extensions

class MkvtoMp4:
    def __init__(self, file, FFMPEG_PATH="FFMPEG.exe", FFPROBE_PATH="FFPROBE.exe", delete=True, output_extension="mp4", audio_bitrate=640):     
        #Get path information from the input file
        output_dir, filename = os.path.split(file)
        filename, input_extension = os.path.splitext(filename)
        input_extension = input_extension[1:]
        
        c = Converter(FFMPEG_PATH, FFPROBE_PATH)
        info = c.probe(file)
        self.height = info.video.video_height
        self.width = info.video.video_width
        if input_extension in valid_input_extensions and output_extension in valid_output_extensions:
            vcodec = "h264"
            print "Video codec detected: " + info.video.codec
            audio_settings = {}
            l = 0
            for a in info.audio:
                print "Audio stream detected: " + a.codec
                print "Channels: " + str(a.audio_channels)
                if a.codec == "aac":
                    acodec = "copy"
                else:
                    acodec = "aac"
                audio_settings.update({l:{
                                    'codec': acodec,
                                    'channels': a.audio_channels,
                                    'bitrate': audio_bitrate,
                                    'language': a.language,
                                    }}) 
                l = l + 1
            subtitle_settings = {}
            l = 0
            for s in info.subtitle:
                print "Subtitle detected: " + s.language
                print "Forced: " + str(s.sub_forced)
                #Going to eventually need settings to go here
                subtitle_settings.update({l:{
                                    'codec': 'mov_text',
                                    'language': s.language
                                    }})
                l = l + 1
            if info.video.codec == "h264" or info.video.codec == "x264":
                vcodec = "copy"
            options = {
                        'format': 'mp4',
                        'video': {
                            'codec': vcodec,
                        },
                        'audio': audio_settings,
                        'subtitle': subtitle_settings,
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