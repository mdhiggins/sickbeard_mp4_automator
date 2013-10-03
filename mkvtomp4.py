import os
import time
import json
import shutil
from converter import Converter
from extensions import valid_input_extensions, valid_output_extensions, bad_subtitle_codecs, valid_subtitle_extensions
from qtfaststart import processor, exceptions


class MkvtoMp4:
    def __init__(self, settings=None, FFMPEG_PATH="FFMPEG.exe", FFPROBE_PATH="FFPROBE.exe", delete=True, output_extension='mp4', output_dir=None, relocate_moov=True, video_codec='h264', audio_codec='aac', audio_bitrate=None, iOS=False, awl=None, swl=None, adl=None, sdl=None, processMP4=False):
        # Settings
        self.FFMPEG_PATH=FFMPEG_PATH
        self.FFPROBE_PATH=FFPROBE_PATH
        self.delete=delete
        self.output_extension=output_extension
        self.output_dir=output_dir
        self.relocate_moov=relocate_moov
        self.processMP4=processMP4
        #Video settings
        self.video_codec=video_codec
        #Audio settings
        self.audio_codec=audio_codec
        self.audio_bitrate=audio_bitrate
        self.iOS=iOS
        self.awl=awl
        self.adl=adl
        #Subtitle settings
        self.swl=swl
        self.sdl=sdl

        #Import settings
        if settings is not None:
            try:
                self.importSettings(settings)
            except:
                pass
        self.options = None

    def importSettings(self, readSettings):
        self.FFMPEG_PATH=readSettings.ffmpeg
        self.FFPROBE_PATH=readSettings.ffprobe
        self.delete=readSettings.delete
        self.output_extension=readSettings.output_extension
        self.output_dir=readSettings.output_dir
        self.relocate_moov=readSettings.relocate_moov
        self.processMP4=readSettings.processMP4
        #Video settings
        #self.video_codec=readSettings.vcodec
        #Audio settings
        self.audio_codec=readSettings.acodec
        #self.audio_bitrate=readSettings.abitrate
        self.iOS=readSettings.iOS
        self.awl=readSettings.awl
        self.adl=readSettings.adl
        #Subtitle settings
        self.swl=readSettings.swl
        self.sdl=readSettings.sdl


    def checkSource(self, inputfile):
        input_dir, filename, input_extension = self.parseFile(inputfile)
        if os.path.isfile(inputfile) is False:
            return False
        if (input_extension in valid_input_extensions or (self.processMP4 is True and input_extension in valid_output_extensions)) and self.output_extension in valid_output_extensions:
            return 0
        elif input_extension in valid_output_extensions and self.processMP4 is False:
            return 1
        else:
            return False


    def readSource(self, inputfile):    
        self.inputfile = inputfile
        #Get path information from the input file
        input_dir, filename, input_extension = self.parseFile(inputfile)
    

        source = self.checkSource(inputfile)
        # Make sure input and output extensions are compatible. If processMP4 is true, then make sure the input extension is a valid output extension and allow to proceed as well
        self.c = Converter(self.FFMPEG_PATH, self.FFPROBE_PATH) 
        if source is 0:
            print inputfile + " detected for potential conversion - processing"

            info = self.c.probe(inputfile)
            self.setDimensions(info)
            
            #Video stream
            print "Video codec detected: " + info.video.codec
            vcodec = 'copy' if info.video.codec == self.video_codec else self.video_codec

            #Audio streams
            audio_settings = {}
            l = 0
            for a in info.audio:
                print "Audio stream detected: " + a.codec + " " + a.language + " [Stream " + str(a.index) + "]"
                # Set undefined language to default language if specified
                if self.adl is not None and a.language == 'und':
                    print "Undefined language detected, defaulting to " + self.adl
                    a.language = self.adl
                # Proceed if no whitelist is set, or if the language is in the whitelist
                if self.awl is None or a.language in self.awl:
                    # Create iOS friendly audio stream if the default audio stream has too many channels (iOS only likes AAC stereo)
                    if self.iOS:
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
                    acodec = 'aac' if self.iOS and a.audio_channels == 2 else self.audio_codec
                    # If desired codec is the same as the source codec, copy to avoid quality loss
                    acodec = 'copy' if a.codec == acodec else acodec

                    # Bitrate calculations/overrides
                    if self.audio_bitrate is None or self.audio_bitrate > (a.audio_channels * 256):
                        abitrate = 256 * a.audio_channels
                    else:
                        abitrate = self.audio_bitrate

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
                    if self.sdl is not None and s.language == 'und':
                        s.language = self.sdl
                    # Proceed if no whitelist is set, or if the language is in the whitelist
                    if self.swl is None or s.language in self.swl:
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
            for dirName, subdirList, fileList in os.walk(input_dir):
                # Walk through files in the same directory as input video
                for fname in fileList:
                    subname, subextension = os.path.splitext(fname)
                    # Watch for appropriate file extension
                    if subextension[1:] in valid_subtitle_extensions:
                        x, lang = os.path.splitext(subname)
                        # If subtitle file name and input video name are the same, proceed
                        if x == filename and len(lang) is 3:
                            print "External subtitle file detected, language " + lang[1:]
                            if self.swl is None or lang[1:] in self.swl:
                                print "Importing %s subtitle stream" % (fname)
                                subtitle_settings.update({l: {
                                    'path': os.path.join(input_dir, fname),
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

            self.inputfile = inputfile
            self.options = options
            return True

        # If file is already in the correct format:
        elif source is 1:
            print "%s detected for potential conversion - already correct format, skipping reprocessing" % (inputfile)
            self.inputfile = inputfile
            self.setDimensions(self.c.probe(inputfile))
            self.options = None
            return None
        # If all else fails
        else:
            print "%s detected for potential conversion - file not in the correct format, ignoring" % (inputfile)
            return False

    def convert(self, reportProgress=False):
        input_dir, filename, input_extension = self.parseFile(self.inputfile)
        output_dir = input_dir if self.output_dir is None else self.output_dir
        outputfile = os.path.join(output_dir, filename + "." + self.output_extension)
        delete = self.delete
        #If we're processing a file that's going to have the same input and output filename, resolve the potential future naming conflict
        if self.options is not None:
            if self.inputfile == outputfile:
                newfile = os.path.join(input_dir, filename + '.tmp.' + self.input_extension)
                #Make sure there isn't any leftover temp files for whatever reason
                self.removeFile(newfile, 0, 0)
                #Attempt to rename the new input file to a temporary name
                try:
                    os.rename(self.inputfile, newfile)
                    self.inputfile = newfile
                except: 
                    i = 1
                    while os.path.isfile(outputfile):
                        outputfile = os.path.join(output_dir, filename + "(" + str(i) + ")." + self.output_extension)
                        i += i

            conv = self.c.convert(self.inputfile, outputfile, self.options, timeout=None)

            if reportProgress:
                import sys
                print json.dumps(self.options, sort_keys=False, indent=4)

            for timecode in conv:
                if reportProgress:
                    sys.stdout.write('[{0}] {1}%\r'.format('#' * (timecode / 10) + ' ' * (10 - (timecode / 10)), timecode))
                    sys.stdout.flush()
            print outputfile + " created"
        else:
            if self.output_dir is not None:
                try:
                    shutil.copy(self.inputfile, outputfile)
                except Exception as e:
                    print "Error moving file to output directory"
                    print e
                    delete = False
                    outputfile = self.inputfile
            else:
                delete = False

        # Set permissions of newly created file
        os.chmod(outputfile, 0777)

        # Attempt to delete the input source file
        if delete:
            if self.removeFile(self.inputfile):
                print self.inputfile + " deleted"
            else:
                print "Couldn't delete the original file:" + self.inputfile
        self.output = outputfile
        return {'file': outputfile,
                'width': self.width,
                'height': self.height }

    def parseFile(self, path):
        input_dir, filename = os.path.split(path)
        filename, input_extension = os.path.splitext(filename)
        input_extension = input_extension[1:]
        return input_dir, filename, input_extension

    def QTFS(self):
        outputfile = self.output
        # Relocate MOOV atom to the very beginning. Can double the time it takes to convert a file but makes streaming faster
        if self.parseFile(outputfile)[2] in valid_output_extensions:
            print "Relocating MOOV atom to start of file"
            tmp = outputfile + ".tmp"
            # Clear out the temp file if it exists
            self.removeFile(tmp, 0, 0)

            try:
                processor.process(outputfile, tmp)
                os.chmod(tmp, 0777)
                # Cleanup
                if self.removeFile(outputfile, replacement=tmp):
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
