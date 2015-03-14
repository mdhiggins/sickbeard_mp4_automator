from __future__ import unicode_literals
import os
import time
import json
import sys
import shutil
import logging
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
                    video_bitrate=None, 
                    audio_codec=['ac3'], 
                    audio_bitrate=256, 
                    iOS=False, 
                    iOSFirst=False,
                    maxchannels=None,
                    awl=None, 
                    swl=None, 
                    adl=None, 
                    sdl=None, 
                    downloadsubs=True,
                    processMP4=False, 
                    copyto=None, 
                    moveto=None,
                    embedsubs=True,
                    providers=['addic7ed', 'podnapisi', 'thesubdb', 'opensubtitles'],
                    permissions=0777,
                    logger=None):
        # Setup Logging
        if logger:
            self.log = logger
        else:
            self.log = logging.getLogger(__name__)

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
        self.permissions=permissions
        # Video settings
        self.video_codec=video_codec
        self.video_bitrate=video_bitrate
        # Audio settings
        self.audio_codec=audio_codec
        self.audio_bitrate=audio_bitrate
        self.iOS=iOS
        self.iOSFirst=iOSFirst
        self.maxchannels=maxchannels
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
        self.permissions = settings.permissions
        #Video settings
        self.video_codec=settings.vcodec
        self.video_bitrate=settings.vbitrate
        #Audio settings
        self.audio_codec=settings.acodec
        self.audio_bitrate=settings.abitrate
        self.iOS=settings.iOS
        self.iOSFirst=settings.iOSFirst
        self.maxchannels=settings.maxchannels
        self.awl=settings.awl
        self.adl=settings.adl
        #Subtitle settings
        self.swl=settings.swl
        self.sdl=settings.sdl
        self.downloadsubs=settings.downloadsubs
        self.subproviders=settings.subproviders
        self.embedsubs=settings.embedsubs

        self.log.debug("Settings imported.")

    # Process a file from start to finish, with checking to make sure formats are compatible with selected settings
    def process(self, inputfile, reportProgress=False, original=None):

        self.log.debug("Process started.")

        delete = self.delete
        deleted = False
        options = None
        if not self.validSource(inputfile): return False

        if self.needProcessing(inputfile):
            options = self.generateOptions(inputfile, original=original)
            try:
                if reportProgress: print json.dumps(options, sort_keys=False, indent=4)
            except:
                pass
            outputfile, inputfile = self.convert(inputfile, options, reportProgress)
            if not outputfile: return False
        else:
            outputfile = inputfile
            if self.output_dir is not None:
                try:                
                    outputfile = os.path.join(self.output_dir, os.path.split(inputfile)[1])
                    shutil.copy(inputfile, outputfile)
                except Exception as e:
                    self.log.exception("Error moving file to output directory.")
                    delete = False
            else:
                delete = False

        if delete:
            if self.removeFile(inputfile):
                try:
                    self.log.debug("%s deleted." % inputfile)
                except:
                    self.log.debug("Original file deleted.")
                deleted = True
            else:
                self.log.error("Couldn't delete the original file: %s." % inputfile)
        if self.downloadsubs:
            for subfile in self.deletesubs:
                if self.removeFile(subfile):
                    try:
                        self.log.debug("Subtitle %s deleted." % subfile)
                    except:
                        self.log.debug("Subtitle file deleted.")

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
            self.log.debug("%s is valid." % inputfile)
            return True
        else:
            self.log.debug("%s is invalid." % inputfile)
            return False            

    # Determine if a file meets the criteria for processing
    def needProcessing(self, inputfile):
        input_dir, filename, input_extension = self.parseFile(inputfile)
        # Make sure input and output extensions are compatible. If processMP4 is true, then make sure the input extension is a valid output extension and allow to proceed as well
        if (input_extension in valid_input_extensions or (self.processMP4 is True and input_extension in valid_output_extensions)) and self.output_extension in valid_output_extensions:
            self.log.debug("%s needs processing." % inputfile)
            return True
        else:
            self.log.debug("%s does not need processing." % inputfile)
            return False

    # Get values for width and height to be passed to the tagging classes for proper HD tags
    def getDimensions(self, inputfile):
        if self.validSource(inputfile): info = Converter(self.FFMPEG_PATH, self.FFPROBE_PATH).probe(inputfile)
        
        self.log.debug("Height: %s" % info.video.video_height)
        self.log.debug("Width: %s" % info.video.video_width)
        return { 'y': info.video.video_height,
                 'x': info.video.video_width }

    # Generate a list of options to be passed to FFMPEG based on selected settings and the source file parameters and streams
    def generateOptions(self, inputfile, original=None):    
        #Get path information from the input file
        input_dir, filename, input_extension = self.parseFile(inputfile)

        info = Converter(self.FFMPEG_PATH, self.FFPROBE_PATH).probe(inputfile)

        #Video stream
        self.log.info("Reading video stream.")
        self.log.info("Video codec detected: %s" % info.video.codec)

        if self.video_bitrate is not None and info.format.bitrate > self.video_bitrate:
            self.log.debug("Overriding video bitrate. Codec cannot be copied because video bitrate is too high.")
            vcodec = self.video_codec[0]
            vbitrate = self.video_bitrate
        else:
            vcodec = 'copy' if info.video.codec.lower() in self.video_codec else self.video_codec[0]
            vbitrate = info.format.bitrate

        #Audio streams
        self.log.info("Reading audio streams.")
        audio_settings = {}
        l = 0
        for a in info.audio:
            try:
                if a.metadata['language'].strip() == "" or a.metadata['language'] is None:
                    a.metadata['language'] = 'und'
            except KeyError:
                a.metadata['language'] = 'und'

            self.log.info("Audio stream #%s detected: %s [%s]." % (a.index, a.codec, a.metadata['language']))

            # Set undefined language to default language if specified
            if self.adl is not None and a.metadata['language'] == 'und':
                self.log.debug("Undefined language detected, defaulting to [%s]." % self.adl)
                a.metadata['language'] = self.adl

            # Proceed if no whitelist is set, or if the language is in the whitelist
            if self.awl is None or a.metadata['language'].lower() in self.awl:
                # Create iOS friendly audio stream if the default audio stream has too many channels (iOS only likes AAC stereo)
                if self.iOS:
                    if a.audio_channels > 2:
                        self.log.info("Creating audio stream %s from source audio stream %s because iOS option is True." % (str(l), a.index))
                        self.log.debug("Audio codec: %s." % self.iOS)
                        self.log.debug("Channels: 2.")
                        self.log.debug("Bitrate: 256.")
                        self.log.debug("Language: %s" % a.metadata['language'])
                        audio_settings.update({l: {
                            'map': a.index,
                            'codec': self.iOS,
                            'channels': 2,
                            'bitrate': 256,
                            'language': a.metadata['language'],
                        }})
                        l += 1
                # If the iOS audio option is enabled and the source audio channel is only stereo, the additional iOS channel will be skipped and a single AAC 2.0 channel will be made regardless of codec preference to avoid multiple stereo channels
                self.log.info("Creating audio stream %s from source audio stream %s." % (str(l), a.index))
                if self.iOS and a.audio_channels <= 2:
                    self.log.debug("Overriding default channel settings because iOS audio is enabled but the source is stereo. Transferring iOS-style settings.")
                    acodec = 'copy' if a.codec == self.iOS else self.iOS
                    audio_channels = a.audio_channels
                    abitrate = a.audio_channels * 128
                else:
                    # If desired codec is the same as the source codec, copy to avoid quality loss
                    acodec = 'copy' if a.codec.lower() in self.audio_codec else self.audio_codec[0]
                    # Audio channel adjustments
                    if self.maxchannels and a.audio_channels > self.maxchannels:
                        audio_channels = self.maxchannels
                        if acodec == 'copy':
                            acodec = self.audio_codec[0]
                        abitrate = self.maxchannels * self.audio_bitrate
                    else:
                        audio_channels = a.audio_channels
                        abitrate = a.audio_channels * self.audio_bitrate
                    # Bitrate calculations/overrides
                    if self.audio_bitrate is 0:
                        abitrate = a.bitrate

                self.log.debug("Audio codec: %s." % acodec)
                self.log.debug("Channels: %s." % audio_channels)
                self.log.debug("Bitrate: %s." % abitrate)
                self.log.debug("Language: %s" % a.metadata['language'])

                # If the iOSFirst option is enabled, disable the iOS option after the first audio stream is processed
                if self.iOS and self.iOSFirst:
                    self.log.debug("Not creating any additional iOS audio streams.")
                    self.iOS = False

                audio_settings.update({l: {
                    'map': a.index,
                    'codec': acodec,
                    'channels': audio_channels,
                    'bitrate': abitrate,
                    'language': a.metadata['language'],
                }})
                l = l + 1

        # Subtitle streams
        subtitle_settings = {}
        l = 0
        self.log.info("Reading subtitle streams.")
        for s in info.subtitle:
            try:
                if s.metadata['language'].strip() == "" or s.metadata['language'] is None:
                    s.metadata['language'] = 'und'
            except KeyError:
                s.metadata['language'] = 'und'

            self.log.info("Subtitle stream #%s detected: %s [%s]." % (s.index, s.codec, s.metadata['language']))

            # Set undefined language to default language if specified
            if self.sdl is not None and s.metadata['language'] == 'und':
                self.log.debug("Undefined language detected, defaulting to [%s]." % self.sdl)
                s.metadata['language'] = self.sdl
            # Make sure its not an image based codec
            if s.codec.lower() not in bad_subtitle_codecs and self.embedsubs:
                
                # Proceed if no whitelist is set, or if the language is in the whitelist
                if self.swl is None or s.metadata['language'].lower() in self.swl:
                    subtitle_settings.update({l: {
                        'map': s.index,
                        'codec': 'mov_text',
                        'language': s.metadata['language']
                        #'forced': s.sub_forced,
                        #'default': s.sub_default
                    }})
                    self.log.info("Creating subtitle stream %s from source subtitle stream %s." % (l, s.index))
                    l = l + 1
            elif s.codec.lower() not in bad_subtitle_codecs and not self.embedsubs:
                if self.swl is None or s.metadata['language'].lower() in self.swl:
                    ripsub = {1: {
                        'map': s.index,
                        'codec': 'srt',
                        'language': s.metadata['language']
                    }}
                    options = {
                        'format': 'srt',
                        'subtitle': ripsub,
                    }
                    input_dir, filename, input_extension = self.parseFile(inputfile)
                    output_dir = input_dir if self.output_dir is None else self.output_dir
                    outputfile = os.path.join(output_dir, filename + "." + s.metadata['language'] + ".srt")
                    
                    i = 2
                    while os.path.isfile(outputfile):
                        outputfile = os.path.join(output_dir, filename + "." + s.metadata['language'] + "." + str(i) + ".srt")
                        i += i
                    self.log.info("Ripping [%s] subtitle from source into external file." % s.metadata['language'])
                    conv = Converter(self.FFMPEG_PATH, self.FFPROBE_PATH).convert(inputfile, outputfile, options, timeout=None)
                    for timecode in conv:
                            pass

                    try:
                        self.log.info("%s created." % outputfile)
                    except:
                        print "Subtitle file created"

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
            self.log.info("Attempting to download subtitles.")
            try:
                subliminal.cache_region.configure('dogpile.cache.memory')
            except:
                pass

            try:
                video = subliminal.scan_video(os.path.abspath(inputfile.decode(sys.getfilesystemencoding())), subtitles=True, embedded_subtitles=True, original=original)
                subtitles = subliminal.download_best_subtitles([video], languages, hearing_impaired=False, providers=self.subproviders)
                subliminal.save_subtitles(subtitles)
            except Exception as e:
                self.log.debug("Unable to download subtitles.")

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
                            self.log.info("External subtitle file detected [%s]." % lang)
                            if self.swl is None or lang in self.swl:
                                try:
                                    self.log.info("Creating subtitle stream %s by importing %s." % (l, fname))
                                except:
                                    self.log.info("Creating subtitle stream %s by importing external file." & l)
                                subtitle_settings.update({l: {
                                    'path': os.path.join(dirName, fname),
                                    'source': src,
                                    'map': 0,
                                    'codec': 'mov_text',
                                    'language': lang,
                                    }})

                                self.log.debug("Path: %s." % os.path.join(dirName, fname))
                                self.log.debug("Source: %s." % src)
                                self.log.debug("Codec: mov_text.")
                                self.log.debug("Langauge: %s." % lang)

                                l = l + 1
                                src = src + 1

                                self.deletesubs.add(os.path.join(dirName, fname))
                            
                            else:
                                self.log.info("Ignoring %s external subtitle stream due to language %s." % (fname, lang))

        # Collect all options
        options = {
            'format': self.output_format,
            'video': {
                'codec': vcodec,
                'map': info.video.index,
                'bitrate': vbitrate
            },
            'audio': audio_settings,
            'subtitle': subtitle_settings,
        }
        self.options = options
        return options

    # Encode a new file based on selected options, built in naming conflict resolution
    def convert(self, inputfile, options, reportProgress=False):
        self.log.info("Starting conversion.")

        input_dir, filename, input_extension = self.parseFile(inputfile)
        output_dir = input_dir if self.output_dir is None else self.output_dir
        outputfile = os.path.join(output_dir.decode(sys.getfilesystemencoding()), filename.decode(sys.getfilesystemencoding()) + "." + self.output_extension).encode(sys.getfilesystemencoding())

        self.log.debug("Input directory: %s." % input_dir)
        self.log.debug("File name: %s." % filename)
        self.log.debug("Input extension: %s." % input_extension)
        self.log.debug("Output directory: %s." % output_dir)
        self.log.debug("Output file: %s." % outputfile)

        if os.path.abspath(inputfile) == os.path.abspath(outputfile):
            self.log.debug("Inputfile and outputfile are the same.")
            newfile = os.path.join(input_dir, filename + '.tmp.' + input_extension)
            #Make sure there isn't any leftover temp files for whatever reason
            if os.path.exists(newfile):
                self.removeFile(newfile, 0, 0)
            #Attempt to rename the new input file to a temporary name
            try:
                os.rename(inputfile, newfile)
                self.log.debug("Input file renamed from %s to %s." % (inputfile, newfile))
                inputfile = newfile
            except: 
                i = 1
                while os.path.isfile(outputfile):
                    outputfile = os.path.join(output_dir, filename + "(" + str(i) + ")." + self.output_extension)
                    i += i
                self.log.debug("Unable to rename input file. Setting output file name to %s." % outputfile)

        conv = Converter(self.FFMPEG_PATH, self.FFPROBE_PATH).convert(inputfile, outputfile, options, timeout=None)

        for timecode in conv:
            if reportProgress:
                sys.stdout.write('[{0}] {1}%\r'.format('#' * (timecode / 10) + ' ' * (10 - (timecode / 10)), timecode))
                sys.stdout.flush()
        try:
            self.log.info("%s created." % outputfile)
        except:
            self.log.info("New media file created.")
        
        try:
            os.chmod(outputfile, self.permissions) # Set permissions of newly created file
        except:
            self.log.exception("Unable to set new file permissions.")
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
            self.log.info("Relocating MOOV atom to start of file.")
            
            outputfile = inputfile.decode(sys.getfilesystemencoding()) + temp_ext

            # Clear out the temp file if it exists
            if os.path.exists(outputfile):
                self.removeFile(outputfile, 0, 0)

            try:
                processor.process(inputfile, outputfile)
                try:
                    os.chmod(outputfile, self.permissions)
                except:
                    self.log.exception("Unable to set file permissions.")
                # Cleanup
                if self.removeFile(inputfile, replacement=outputfile):
                    return outputfile
                else:
                    self.log.error("Error cleaning up QTFS temp files.")
                    return False
            except exceptions.FastStartException:
                self.log.warning("QT FastStart did not run - perhaps moov atom was at the start already.")
                return inputfile

    # Makes additional copies of the input file in each directory specified in the copy_to option
    def replicate(self, inputfile, relativePath=None):
        if self.copyto:
            self.log.debug("Copyto option is enabled.")
            for d in self.copyto:
                if (relativePath):
                    d = os.path.join(d, relativePath)
                    if not os.path.exists(d):
                        os.makedirs(d)
                try:
                    shutil.copy(inputfile, d)
                    self.log.info("%s copied to %s." % (inputfile, d))
                except UnicodeDecodeError:
                    self.log.info("File copied.")
                except Exception as e:
                    try:
                        shutil.copy(inputfile.decode(sys.getfilesystemencoding()), d)
                        self.log.info("%s copied to %s." % (inputfile, d))
                    except UnicodeDecodeError:
                        self.log.info("File copied.")
                    except Exception as e:
                        self.log.exception("Unable to create additional copy of file in %s." % (d))

        if self.moveto:
            self.log.debug("Moveto option is enabled.")
            moveto = os.path.join(self.moveto, relativePath) if relativePath else self.moveto
            if not os.path.exists(moveto):
                os.makedirs(moveto)
            try:
                shutil.move(inputfile, moveto)
                self.log.info("%s moved to %s" % (moveto))
            except UnicodeDecodeError:
                self.log.info("File moved.")
            except Exception as e:
                try:
                    shutil.move(inputfile.decode(sys.getfilesystemencoding()), moveto)
                    self.log.info("%s moved to %s" % (moveto))
                except UnicodeDecodeError:
                    self.log.info("File moved.")
                except Exception as e:
                    self.log.exception("Unable to move file to %s" % (moveto))

    # Robust file removal function, with options to retry in the event the file is in use, and replace a deleted file
    def removeFile(self, filename, retries=2, delay=10, replacement=None):
        for i in range(retries + 1):
            try:
                # Make sure file isn't read-only
                os.chmod(filename, 0777)
            except:
                self.log.debug("Unable to chmod file before deletion.")
            try:
                os.remove(filename)
                # Replaces the newly deleted file with another by renaming (replacing an original with a newly created file)
                if replacement is not None:
                    try:
                        os.rename(replacement, filename)
                        filename = replacement
                    except:
                        self.log.exception("Unable to rename file.")
                break
            except OSError:
                self.log.exception("Unable to remove file %s." % filename)
                if delay > 0:
                    self.log.debug("Delaying for %s seconds before retrying." % delay)
                    time.sleep(delay)
        return False if os.path.isfile(filename) else True
