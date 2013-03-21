import os
import sys
import time
from converter import Converter
from extensions import valid_input_extensions, valid_output_extensions
from qtfaststart import processor


class MkvtoMp4:
    def __init__(self, file, FFMPEG_PATH="FFMPEG.exe", FFPROBE_PATH="FFPROBE.exe", delete=True, output_extension='mp4', relocate_moov=True, video_codec='h264', audio_codec='aac', audio_bitrate=None, iOS=False, awl=None, swl=None, adl=None, sdl=None):
        #Get path information from the input file
        output_dir, filename = os.path.split(file)
        filename, input_extension = os.path.splitext(filename)
        input_extension = input_extension[1:]

        c = Converter(FFMPEG_PATH, FFPROBE_PATH)
        # Get values for width and height to be passed to the tagging classes for proper HD tags
        info = c.probe(file)
        self.height = info.video.video_height
        self.width = info.video.video_width
        # Make sure input and output extensions are compatible
        if input_extension in valid_input_extensions and output_extension in valid_output_extensions:

            #Video stream
            print "Video codec detected: " + info.video.codec
            vcodec = 'copy' if info.video.codec == video_codec else video_codec

            #Audio streams
            audio_settings = {}
            l = 0
            for a in info.audio:
                print "Audio stream detected: " + a.codec
                # Set undefined language to default language if specified
                if adl is not None and a.language == 'und':
                    a.language = adl
                # Proceed if no whitelist is set, or if the language is in the whitelist
                if awl is None or a.language in awl:
                    # Create iOS friendly audio stream if the default audio stream has too many channels (iOS only likes AAC stereo)
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

                    # Bitrate calculations/overrides
                    if audio_bitrate is None or audio_bitrate > (a.audio_channels * 256):
                        abitrate = 256 * a.audio_channels
                    else:
                        abitrate = audio_bitrate
                    print abitrate

                    audio_settings.update({l: {
                        'map': a.index,
                        'codec': acodec,
                        'channels': a.audio_channels,
                        'bitrate': abitrate,
                        'language': a.language,
                    }})
                    l = l + 1

            # Subtitle streams
            subtitle_settings = {}
            l = 0
            for s in info.subtitle:
                print "Subtitle stream detected: " + s.language
                # Set undefined language to default language if specified
                if sdl is not None and s.language == 'und':
                    s.language = sdl
                # Proceed if no whitelist is set, or if the language is in the whitelist
                if swl is None or s.language in swl:
                    subtitle_settings.update({l: {
                        'map': s.index,
                        'codec': 'mov_text',
                        'language': s.language,
                        'forced': s.sub_forced,
                        'default': s.sub_default
                    }})
                    l = l + 1

            # Collect all options
            options = {
                'format': 'mp4',
                'video': {
                    'codec': vcodec,
                    'map': info.video.index,
                    'bitrate': info.format.bitrate
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

            # Attempt to delete the input source file
            if delete:
                try:
                    os.remove(file)
                    print file + " deleted"
                except OSError:
                    print "Unable to delete " + file

        # If file is already in the correct format:
        elif input_extension in valid_output_extensions:
            self.output = file

        # If all else fails
        else:
            print file + " - file not in the correct format"
            sys.exit()

        # Relocate MOOV atom to the very beginning. Can double the time it takes to convert a file but makes streaming faster
        if (relocate_moov):
            print "Relocating MOOV atom to start of file"
            tmp = self.output + ".tmp"
            try:
                os.remove(tmp)
            except OSError:
                pass
            for i in range(3):
                try:
                    os.rename(self.output, tmp)
                    break
                except WindowsError:
                    time.sleep(10)
            processor.process(tmp, self.output)
            os.remove(tmp)
