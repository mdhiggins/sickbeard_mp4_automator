from __future__ import unicode_literals
import os
import time
import json
import sys
import shutil
from converter import Converter
from extensions import valid_input_extensions, valid_output_extensions, bad_subtitle_codecs, valid_subtitle_extensions
from qtfaststart import processor, exceptions
from babelfish import Language


class MkvtoMp4:
    def __init__(   self, settings=None, 
                    FFMPEG_PATH="FFMPEG.exe", 
                    FFPROBE_PATH="FFPROBE.exe", 
                    delete=True, 
                    output_extension='mp4', 
                    output_dir=None, 
                    relocate_moov=True, 
                    output_format = 'mp4', 
                    video_codec=['h264', 'x264'], 
                    audio_codec=['ac3'], 
                    audio_bitrate=None, 
                    iOS=False, 
                    awl=None, 
                    swl=None, 
                    adl=None, 
                    sdl=None, 
                    downloadsubs=True,
                    processMP4=False, 
                    copyto=None, 
                    moveto=None,
                    embedsubs=True,
                    providers=['addic7ed', 'podnapisi', 'thesubdb', 'opensubtitles']):
        # Settings
        self.FFMPEG_PATH=FFMPEG_PATH
        self.FFPROBE_PATH=FFPROBE_PATH
        self.delete=delete
        self.output_extension=output_extension
        self.output_format=output_format
        self.output_dir=output_dir
        self.relocate_moov=relocate_moov
        self.processMP4=processMP4
        self.copyto=copyto
        self.moveto=moveto
        self.relocate_moov=relocate_moov
        # Video settings
        self.video_codec=video_codec
        # Audio settings
        self.audio_codec=audio_codec
        self.audio_bitrate=audio_bitrate
        self.iOS=iOS
        self.awl=awl
        self.adl=adl
        # Subtitle settings
        self.swl=swl
        self.sdl=sdl
        self.downloadsubs = downloadsubs
        self.subproviders = providers
        self.embedsubs = embedsubs

        # Import settings
        if settings is not None: self.importSettings(settings)
        self.options = None
        self.deletesubs = set()

    def importSettings(self, settings):
        self.FFMPEG_PATH=settings.ffmpeg
        self.FFPROBE_PATH=settings.ffprobe
        self.delete=settings.delete
        self.output_extension=settings.output_extension
        self.output_format=settings.output_format
        self.output_dir=settings.output_dir
        self.relocate_moov=settings.relocate_moov
        self.processMP4=settings.processMP4
        self.copyto=settings.copyto
        self.moveto=settings.moveto
        self.relocate_moov = settings.relocate_moov
        #Video settings
        self.video_codec=settings.vcodec
        #Audio settings
        self.audio_codec=settings.acodec
        #self.audio_bitrate=settings.abitrate
        self.iOS=settings.iOS
        self.awl=settings.awl
        self.adl=settings.adl
        #Subtitle settings
        self.swl=settings.swl
        self.sdl=settings.sdl
        self.downloadsubs=settings.downloadsubs
        self.subproviders=settings.subproviders
        self.embedsubs=settings.embedsubs

    # Process a file from start to finish, with checking to make sure formats are compatible with selected settings
    def process(self, inputfile, reportProgress=False, original=None):
        delete = self.delete
        deleted = False
        options = None
        if not self.validSource(inputfile): return False

        if self.needProcessing(inputfile):
            options = self.generateOptions(inputfile, original=original)
            if reportProgress: print json.dumps(options, sort_keys=False, indent=4)
            outputfile, inputfile = self.convert(inputfile, options, reportProgress)
            if not outputfile: return False
        else:
            outputfile = inputfile
            if self.output_dir is not None:
                try:                
                    outputfile = os.path.join(self.output_dir, os.path.split(inputfile)[1])
                    shutil.copy(inputfile, outputfile)
                except Exception as e:
                    print "Error moving file to output directory"
                    print e
                    delete = False
            else:
                delete = False



        if delete:
            if self.removeFile(inputfile):
                try:
                    print inputfile + " deleted"
                except:
                    print "Original file deleted"
                deleted = True
            else:
                print "Couldn't delete the original file:" + inputfile
            if self.downloadsubs:
                for subfile in self.deletesubs:
                    if self.removeFile(subfile):
                        print subfile + "deleted"

        dim = self.getDimensions(outputfile)

        return { 'input': inputfile,
                 'output': outputfile,
                 'options': options,
                 'input_deleted': deleted,
                 'x': dim['x'],
                 'y': dim['y'] }

    # Determine if a source video file is in a valid format
    def validSource(self, inputfile):
        input_dir, filename, input_extension = self.parseFile(inputfile)
        # Make sure the input_extension is some sort of recognized extension, and that the file actually exists
        if (input_extension in valid_input_extensions or input_extension in valid_output_extensions) and os.path.isfile(inputfile):
            return True
        else:
            return False            

    # Determine if a file meets the criteria for processing
    def needProcessing(self, inputfile):
        input_dir, filename, input_extension = self.parseFile(inputfile)
        # Make sure input and output extensions are compatible. If processMP4 is true, then make sure the input extension is a valid output extension and allow to proceed as well
        if (input_extension in valid_input_extensions or (self.processMP4 is True and input_extension in valid_output_extensions)) and self.output_extension in valid_output_extensions:
            return True
        else:
            return False

    # Get values for width and height to be passed to the tagging classes for proper HD tags
    def getDimensions(self, inputfile):
        if self.validSource(inputfile): info = Converter(self.FFMPEG_PATH, self.FFPROBE_PATH).probe(inputfile)
        
        return { 'y': info.video.video_height,
                 'x': info.video.video_width }

    # Generate a list of options to be passed to FFMPEG based on selected settings and the source file parameters and streams
    def generateOptions(self, inputfile, original=None):    
        #Get path information from the input file
        input_dir, filename, input_extension = self.parseFile(inputfile)

        info = Converter(self.FFMPEG_PATH, self.FFPROBE_PATH).probe(inputfile)
       
        #Video stream
        print "Video codec detected: " + info.video.codec
        vcodec = 'copy' if info.video.codec in self.video_codec else self.video_codec[0]

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
                            'codec': self.iOS,
                            'channels': 2,
                            'bitrate': 256,
                            'language': a.language,
                        }})
                        l += 1
                # If the iOS audio option is enabled and the source audio channel is only stereo, the additional iOS channel will be skipped and a single AAC 2.0 channel will be made regardless of codec preference to avoid multiple stereo channels
                if self.iOS and a.audio_channels <= 2:
                    acodec = 'copy' if a.codec == 'aac' else self.iOS
                else:
                    # If desired codec is the same as the source codec, copy to avoid quality loss
                    acodec = 'copy' if a.codec in self.audio_codec else self.audio_codec[0]

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

            # Set undefined language to default language if specified
            if self.sdl is not None and s.language == 'und':
                s.language = self.sdl
            # Make sure its not an image based codec
            if s.codec.lower() not in bad_subtitle_codecs and self.embedsubs:
                
                # Proceed if no whitelist is set, or if the language is in the whitelist
                if self.swl is None or s.language in self.swl:
                    subtitle_settings.update({l: {
                        'map': s.index,
                        'codec': 'mov_text',
                        'language': s.language
                        #'forced': s.sub_forced,
                        #'default': s.sub_default
                    }})
                    l = l + 1
            elif s.codec.lower() not in bad_subtitle_codecs and not self.embedsubs:
                if self.swl is None or s.language in self.swl:
                    ripsub = {1: {
                        'map': s.index,
                        'codec': 'srt',
                        'language': s.language
                    }}
                    options = {
                        'format': 'srt',
                        'subtitle': ripsub,
                    }
                    input_dir, filename, input_extension = self.parseFile(inputfile)
                    output_dir = input_dir if self.output_dir is None else self.output_dir
                    outputfile = os.path.join(output_dir, filename + "." + s.language + ".srt")
                    
                    i = 2
                    while os.path.isfile(outputfile):
                        outputfile = os.path.join(output_dir, filename + "." + s.language + "." + str(i) + ".srt")
                        i += i
                    print "Ripping " + s.language + " subtitle from file"
                    conv = Converter(self.FFMPEG_PATH, self.FFPROBE_PATH).convert(inputfile, outputfile, options, timeout=None)
                    for timecode in conv:
                            pass

                    try:
                        print outputfile + " created"
                    except:
                        print "File created"

        # Attempt to download subtitles if they are missing using subliminal
        languages = set()
        if self.swl:
            for alpha3 in self.swl:
                languages.add(Language(alpha3))
        elif self.sdl:
            languages.add(Language(self.sdl))
        else:
            self.downloadsubs = False

        if self.downloadsubs:
            import subliminal
            print "Attempting to download subtitles, please wait"

            try:
                subliminal.cache_region.configure('dogpile.cache.memory')
            except:
                pass

            try:
                video = subliminal.scan_video(os.path.abspath(inputfile), subtitles=True, embedded_subtitles=True, original=original)
                subtitles = subliminal.download_best_subtitles([video], languages, hearing_impaired=False, providers=self.subproviders)
                subliminal.save_subtitles(subtitles)
            except Exception as e:
                print e
                print "Unable to download subtitle"

        # External subtitle import
        if self.embedsubs: #Don't bother if we're not embeddeding any subtitles
            src = 1  # FFMPEG input source number
            for dirName, subdirList, fileList in os.walk(input_dir):
                for fname in fileList:
                    subname, subextension = os.path.splitext(fname)
                    # Watch for appropriate file extension
                    if subextension[1:] in valid_subtitle_extensions:
                        x, lang = os.path.splitext(subname)
                        lang = lang[1:]
                        # Using bablefish to convert a 2 language code to a 3 language code
                        if len(lang) is 2:
                            try:
                                babel = Language.fromalpha2(lang)
                                lang = babel.alpha3
                            except:
                                pass
                        # If subtitle file name and input video name are the same, proceed
                        if x == filename:
                            print "External subtitle file detected, language " + lang
                            if self.swl is None or lang in self.swl:
                                print "Importing %s subtitle stream" % (fname)
                                subtitle_settings.update({l: {
                                    'path': os.path.join(dirName, fname),
                                    'source': src,
                                    'map': 0,
                                    'codec': 'mov_text',
                                    'language': lang,
                                    }})
                                l = l + 1
                                src = src + 1
                                self.deletesubs.add(os.path.join(dirName, fname))
                            else:
                                print "Ignoring %s external subtitle stream due to language: %s" % (fname, lang)

        # Collect all options
        options = {
            'format': self.output_format,
            'video': {
                'codec': vcodec,
                'map': info.video.index,
                'bitrate': info.format.bitrate
            },
            'audio': audio_settings,
            'subtitle': subtitle_settings,
        }
        self.options = options
        return options

    # Encode a new file based on selected options, built in naming conflict resolution
    def convert(self, inputfile, options, reportProgress=False):
        input_dir, filename, input_extension = self.parseFile(inputfile)
        output_dir = input_dir if self.output_dir is None else self.output_dir
        try:
            outputfile = os.path.join(output_dir, filename + "." + self.output_extension)
        except UnicodeDecodeError:
            outputfile = os.path.join(output_dir, filename.decode('utf-8') + "." + self.output_extension)
        #If we're processing a file that's going to have the same input and output filename, resolve the potential future naming conflict
        if os.path.abspath(inputfile) == os.path.abspath(outputfile):
            newfile = os.path.join(input_dir, filename + '.tmp.' + input_extension)
            #Make sure there isn't any leftover temp files for whatever reason
            self.removeFile(newfile, 0, 0)
            #Attempt to rename the new input file to a temporary name
            try:
                os.rename(inputfile, newfile)
                inputfile = newfile
            except: 
                i = 1
                while os.path.isfile(outputfile):
                    outputfile = os.path.join(output_dir, filename + "(" + str(i) + ")." + self.output_extension)
                    i += i

        conv = Converter(self.FFMPEG_PATH, self.FFPROBE_PATH).convert(inputfile, outputfile, options, timeout=None)

        for timecode in conv:
            if reportProgress:
                sys.stdout.write('[{0}] {1}%\r'.format('#' * (timecode / 10) + ' ' * (10 - (timecode / 10)), timecode))
                sys.stdout.flush()
        print outputfile + " created"
        
        os.chmod(outputfile, 0777) # Set permissions of newly created file
        return outputfile, inputfile

    # Break apart a file path into the directory, filename, and extension
    def parseFile(self, path):
        path = os.path.abspath(path)
        input_dir, filename = os.path.split(path)
        filename, input_extension = os.path.splitext(filename)
        input_extension = input_extension[1:]
        return input_dir, filename, input_extension

    # Process a file with QTFastStart, removing the original file
    def QTFS(self, inputfile):
        input_dir, filename, input_extension = self.parseFile(inputfile)
        temp_ext = '.QTFS'
        # Relocate MOOV atom to the very beginning. Can double the time it takes to convert a file but makes streaming faster
        if self.parseFile(inputfile)[2] in valid_output_extensions and os.path.isfile(inputfile) and self.relocate_moov:
            print "Relocating MOOV atom to start of file"
            outputfile = inputfile + temp_ext

            # Clear out the temp file if it exists
            self.removeFile(outputfile, 0, 0)

            try:
                processor.process(inputfile, outputfile)
                os.chmod(outputfile, 0777)
                # Cleanup
                if self.removeFile(inputfile, replacement=outputfile):
                    print 'Temporary file %s deleted' % (inputfile)
                    return outputfile
                else:
                    print "Error cleaning up QTFS temp files"
                    return False
            except exceptions.FastStartException:
                print "QT FastStart did not run - perhaps moov atom was at the start already"
                return inputfile

    # Makes additional copies of the input file in each directory specified in the copy_to option
    def replicate(self, inputfile, relativePath=None):
        if self.copyto:
            for d in self.copyto:
                if (relativePath):
                    d = os.path.join(d, relativePath)
                    if not os.path.exists(d):
                        os.makedirs(d)
                try:
                    print "Attempting to copy file %s to %s" % (inputfile, d)
                except:
                    print "Attempting to copy file"
                try:
                    shutil.copy(inputfile, d)
                    print "Copy succeeded"
                except Exception as e:
                    print "Unable to create additional copy of file in %s" % (d)
                    print e
        if self.moveto:
            moveto = os.path.join(self.moveto, relativePath) if relativePath else self.moveto
            if not os.path.exists(moveto):
                os.makedirs(moveto)
            try:
                shutil.move(inputfile, moveto)
                print "File moved to %s" % (moveto)
            except Exception as e:
                print "Unable to move file to %s" % (moveto)
                print e

    # Robust file removal function, with options to retry in the event the file is in use, and replace a deleted file
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
