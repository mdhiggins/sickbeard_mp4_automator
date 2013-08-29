import os
import sys
import time
from converter import Converter
from extensions import valid_input_extensions, valid_output_extensions, bad_subtitle_codecs, valid_subtitle_extensions
from qtfaststart import processor, exceptions


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
                print "Audio stream detected: " + a.codec + " " + a.language + " [Stream " + str(a.index) + "]"
                # Set undefined language to default language if specified
                if adl is not None and a.language == 'und':
                    print "Undefined language detected, defaulting to " + adl
                    a.language = adl
                # Proceed if no whitelist is set, or if the language is in the whitelist
                if awl is None or a.language in awl:
                    # Create iOS friendly audio stream if the default audio stream has too many channels (iOS only likes AAC stereo)
                    if iOS:
                        if a.audio_channels > 2 or a.codec != 'aac':
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
                print "Subtitle stream detected: " + s.codec + " " + s.language + " [Stream " + str(s.index) + "]"

                # Make sure its not an image based codec
                if s.codec not in bad_subtitle_codecs:
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

            # External subtitle import
            src = 1  # FFMPEG input source number
            for dirName, subdirList, fileList in os.walk(output_dir):
                for fname in fileList:
                    subname, subextension = os.path.splitext(fname)
                    if subextension[1:] in valid_subtitle_extensions:
                        x, lang = os.path.splitext(subname)
                        if x == filename:
                            print "External subtitle file detected, language " + lang[1:]
                            if swl is None or lang[1:] in swl:
                                print "Adding subtitle"
                                subtitle_settings.update({l: {
                                    'path': os.path.join(output_dir, fname),
                                    'source': src,
                                    'map': 0,
                                    'codec': 'mov_text',
                                    'language': lang[1:],
                                    }})
                                l = l + 1
                                src = src + 1
                            else:
                                print "Ignoring subtitle stream due to language"

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
            conv = c.convert(file, self.output, options, None)

            for timecode in conv:
                pass
                #print '[{0}] {1}%'.format('#' * (timecode / 10) + ' ' * (10 - (timecode / 10)), timecode, end='\r')
            print "Conversion complete"

            # Set permissions of newly created file
            os.chmod(self.output, 0777)

            # Attempt to delete the input source file
            if delete:
                if self.removeFile(file):
                    print file + " deleted"
                else:
                    print "Couldn't delete the original file"

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
            # Clear out the temp file if it exists
            self.removeFile(tmp, 0, 0)

            try:
                processor.process(self.output, tmp)
                os.chmod(tmp, 0777)
                # Cleanup
                if self.removeFile(self.output, replacement=tmp):
                    print "Cleanup successful"
                else:
                    print "Error cleaning up temp files and renaming"
            except exceptions.FastStartException:
                print "QT FastStart did not run - perhaps moov atom was at the start already"

    def removeFile(self, filename, retries=2, delay=10, replacement=None):
        for i in range(retries + 1):
            try:
                # Make sure file isn't read-only
                os.chmod(filename, 0777)
                os.remove(filename)
                # Replaces the newly deleted file with another by renaming (replacing an original with a newly created file)
                if replacement is not None:
                    os.rename(replacement, filename)
                    filename = replacement
                break
            except OSError:
                if delay > 0:
                    time.sleep(delay)
        return False if os.path.isfile(filename) else True
