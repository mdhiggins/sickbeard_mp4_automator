import os
import time
import json
from converter import Converter
from extensions import valid_input_extensions, valid_output_extensions, bad_subtitle_codecs, valid_subtitle_extensions
from qtfaststart import processor, exceptions


class MkvtoMp4:
    def __init__(self, file, FFMPEG_PATH="FFMPEG.exe", FFPROBE_PATH="FFPROBE.exe", delete=True, output_extension='mp4', relocate_moov=True, video_codec='h264', audio_codec='aac', audio_bitrate=None, iOS=False, awl=None, swl=None, adl=None, sdl=None, processMP4=False, reportProgress=False):
        #Get path information from the input file
        output_dir, filename = os.path.split(file)
        filename, input_extension = os.path.splitext(filename)
        input_extension = input_extension[1:]
        self.relocate_moov = relocate_moov

        if reportProgress:
            import sys

        c = Converter(FFMPEG_PATH, FFPROBE_PATH)
        
        #If we're processing a file that's going to have the same input and output extension, resolve the potential future naming conflict
        if processMP4 and input_extension == output_extension:
            newfile = os.path.join(output_dir, filename + '.tmp.' + input_extension)
            #Make sure there isn't any leftover temp files for whatever reason
            self.removeFile(newfile, 0, 0)
            #Attempt to rename the new input file to a temporary name
            try:
                os.rename(file, newfile)
                file = newfile
            except: 
                pass
        
        # Make sure input and output extensions are compatible. If processMP4 is true, then make sure the input extension is a valid output extension and allow to proceed as well
        if (input_extension in valid_input_extensions or (processMP4 is True and input_extension in valid_output_extensions)) and output_extension in valid_output_extensions:
            print file + " detected for potential conversion - processing"
            info = c.probe(file)
            self.setDimensions(info)

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
                        if a.audio_channels > 2:
                            print "Creating dual audio channels for iOS compatability for this stream"
                            audio_settings.update({l: {
                                'map': a.index,
                                'codec': 'aac',
                                'channels': 2,
                                'bitrate': 512,
                                'language': a.language,
                            }})
                            l += 1
                    # If the iOS audio option is enabled and the source audio channel is only stereo, the additional iOS channel will be skipped and a single AAC 2.0 channel will be made regardless of codec preference to avoid multiple stereo channels
                    acodec = 'aac' if iOS and a.audio_channels == 2 else audio_codec
                    # If desired codec is the same as the source codec, copy to avoid quality loss
                    acodec = 'copy' if a.codec == acodec else acodec

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
                # Walk through files in the same directory as input video
                for fname in fileList:
                    subname, subextension = os.path.splitext(fname)
                    # Watch for appropriate file extension
                    if subextension[1:] in valid_subtitle_extensions:
                        x, lang = os.path.splitext(subname)
                        # If subtitle file name and input video name are the same, proceed
                        if x == filename and len(lang) is 3:
                            print "External subtitle file detected, language " + lang[1:]
                            if swl is None or lang[1:] in swl:
                                print "Importing %s subtitle stream" % (fname)
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
                                print "Ignoring %s external subtitle stream due to language: %s" % (fname, lang)

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

            print json.dumps(options, sort_keys=False, indent=4)
            self.output = os.path.join(output_dir, filename + "." + output_extension)
            
            # Avoid any residual naming conflicts for files that already exist
            i = 1
            while os.path.isfile(self.output):
                self.output = os.path.join(output_dir, filename + "(" + str(i) + ")." + output_extension)
                i += i

            conv = c.convert(file, self.output, options, timeout=None)

            for timecode in conv:
                if reportProgress:
                    sys.stdout.write('[{0}] {1}%\r'.format('#' * (timecode / 10) + ' ' * (10 - (timecode / 10)), timecode))
                    sys.stdout.flush()
            print self.output + " created"

            # Set permissions of newly created file
            os.chmod(self.output, 0777)

            # Attempt to delete the input source file
            if delete:
                if self.removeFile(file):
                    print file + " deleted"
                else:
                    print "Couldn't delete the original file:" + file

        # If file is already in the correct format:
        elif input_extension in valid_output_extensions and processMP4 is False:
            print file + " detected for potential conversion - already correct format, skipping reprocessing"
            self.setDimensions(c.probe(file))
            self.output = file

        # If all else fails
        else:
            print file + " detected for potential conversion - file not in the correct format, ignoring"
            self.output = None

    def QTFS(self):
        # Relocate MOOV atom to the very beginning. Can double the time it takes to convert a file but makes streaming faster
        if (self.relocate_moov):
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

    def setDimensions(self, info):
        # Get values for width and height to be passed to the tagging classes for proper HD tags
        self.height = info.video.video_height
        self.width = info.video.video_width

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
