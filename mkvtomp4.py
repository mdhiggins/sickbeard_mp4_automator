import os
import sys
from converter import Converter
from extensions import valid_input_extensions, valid_output_extensions
from qtfaststart import processor


class MkvtoMp4:
    def __init__(self, file, FFMPEG_PATH="FFMPEG.exe", FFPROBE_PATH="FFPROBE.exe", delete=True, output_extension='mp4', relocate_moov=True, video_codec='h264', audio_codec='aac', audio_bitrate=640, iOS=False):
        #Get path information from the input file
        output_dir, filename = os.path.split(file)
        filename, input_extension = os.path.splitext(filename)
        input_extension = input_extension[1:]

        c = Converter(FFMPEG_PATH, FFPROBE_PATH)
        info = c.probe(file)
        self.height = info.video.video_height
        self.width = info.video.video_width
        if input_extension in valid_input_extensions and output_extension in valid_output_extensions:
            print "Video codec detected: " + info.video.codec
            vcodec = 'copy' if info.video.codec == video_codec else video_codec
            audio_settings = {}
            l = 0
            for a in info.audio:
                print "Audio stream detected: " + a.codec
                if iOS and a.audio_channels > 2:
                    print "Creating dual audio channels for iOS compatability for this stream"
                    audio_settings.update({l: {
                        'map': a.index,
                        'codec': 'aac',
                        'channels': 2,
                        'bitrate': 512,
                        'language': a.language,
                    }})
                    l += 1
                acodec = 'copy' if a.codec == audio_codec else audio_codec
                if a.audio_channels <= 2 and audio_bitrate > 512:
                    audio_bitrate = 512
                audio_settings.update({l: {
                    'map': a.index,
                    'codec': acodec,
                    'channels': a.audio_channels,
                    'bitrate': audio_bitrate,
                    'language': a.language,
                }})
                l = l + 1
            subtitle_settings = {}
            l = 0
            for s in info.subtitle:
                print "Subtitle stream detected: " + s.language
                subtitle_settings.update({l: {
                    'map': s.index,
                    'codec': 'mov_text',
                    'language': s.language,
                    'forced': s.sub_forced,
                    'default': s.sub_default
                }})
                l = l + 1
            options = {
                'format': 'mp4',
                'video': {
                    'codec': vcodec,
                    'map': info.video.index
                },
                'audio': audio_settings,
                'subtitle': subtitle_settings,
            }
            print options
            self.output = os.path.join(output_dir, filename + "." + output_extension)
            conv = c.convert(file, self.output, options)
            for timecode in conv:
                print '[{0}] {1}%'.format('#' * (timecode / 10) + ' ' * (10 - (timecode / 10)), timecode, end='\r')
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
        if (relocate_moov):
            print "Relocating MOOV atom to start of file"
            tmp = self.output + ".tmp"
            try:
                os.remove(tmp)
            except OSError:
                pass
            os.rename(self.output, tmp)
            processor.process(tmp, self.output)
            os.remove(tmp)
