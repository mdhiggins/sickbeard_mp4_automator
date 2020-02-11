from __future__ import unicode_literals
import os
import time
import json
import sys
import shutil
import logging
from converter import Converter, FFMpegConvertError, ConverterError
from extensions import subtitle_codec_extensions, valid_tagging_extensions
try:
    from babelfish import Language
except:
    pass
try:
    import subliminal
except:
    pass


class MkvtoMp4:
    def __init__(self, settings=None,
                 FFMPEG_PATH="FFMPEG.exe",
                 FFPROBE_PATH="FFPROBE.exe",
                 delete=True,
                 output_extension='mp4',
                 temp_extension=None,
                 output_dir=None,
                 relocate_moov=True,
                 output_format='mp4',
                 video_codec=['h264', 'x264'],
                 video_bitrate=None,
                 vcrf=None,
                 video_width=None,
                 video_profile=None,
                 h264_level=None,
                 qsv_decoder=True,
                 hevc_qsv_decoder=False,
                 dxva2_decoder=False,
                 audio_codec=['ac3'],
                 ignore_truehd=True,
                 audio_bitrate=256,
                 audio_filter=None,
                 audio_copyoriginal=False,
                 audio_first_language_track=False,
                 allow_language_relax=True,
                 sort_streams=False,
                 prefer_more_channels=True,
                 iOS=False,
                 iOSFirst=False,
                 iOSLast=False,
                 iOS_filter=None,
                 maxchannels=None,
                 aac_adtstoasc=False,
                 awl=None,
                 swl=None,
                 adl=None,
                 sdl=None,
                 scodec=['mov_text'],
                 scodec_image=[],
                 subencoding='utf-8',
                 downloadsubs=True,
                 hearing_impaired=False,
                 process_same_extensions=False,
                 forceConvert=False,
                 copyto=None,
                 moveto=None,
                 embedsubs=True,
                 embedonlyinternalsubs=True,
                 providers=['addic7ed', 'podnapisi', 'thesubdb', 'opensubtitles'],
                 permissions={'chmod': int('0755', 8), 'uid': -1, 'gid': -1},
                 pix_fmt=None,
                 logger=None,
                 threads='auto',
                 preopts=None,
                 postopts=None):
        # Setup Logging
        if logger:
            self.log = logger
        else:
            self.log = logging.getLogger(__name__)

        # Settings
        self.FFMPEG_PATH = FFMPEG_PATH
        self.FFPROBE_PATH = FFPROBE_PATH
        self.threads = threads
        self.delete = delete
        self.output_extension = output_extension
        self.temp_extension = temp_extension
        self.output_format = output_format
        self.output_dir = output_dir
        self.relocate_moov = relocate_moov
        self.process_same_extensions = process_same_extensions
        self.forceConvert = forceConvert
        self.copyto = copyto
        self.moveto = moveto
        self.relocate_moov = relocate_moov
        self.permissions = permissions
        self.preopts = preopts
        self.postopts = postopts
        self.sort_streams = sort_streams
        # Video settings
        self.video_codec = video_codec
        self.video_bitrate = video_bitrate
        self.vcrf = vcrf
        self.video_width = video_width
        self.video_profile = video_profile
        self.h264_level = h264_level
        self.qsv_decoder = qsv_decoder
        self.hevc_qsv_decoder = hevc_qsv_decoder
        self.dxva2_decoder = dxva2_decoder
        self.pix_fmt = pix_fmt
        # Audio settings
        self.audio_codec = audio_codec
        self.audio_bitrate = audio_bitrate
        self.audio_filter = audio_filter
        self.iOS = iOS
        self.iOSFirst = iOSFirst
        self.iOSLast = iOSLast
        self.iOS_filter = iOS_filter
        self.maxchannels = maxchannels
        self.awl = awl
        self.adl = adl
        self.ignore_truehd = ignore_truehd
        self.aac_adtstoasc = aac_adtstoasc
        self.audio_copyoriginal = audio_copyoriginal
        self.audio_first_language_track = audio_first_language_track
        self.allow_language_relax = allow_language_relax
        self.prefer_more_channels = prefer_more_channels
        # Subtitle settings
        self.scodec = scodec
        self.scodec_image = scodec_image
        self.swl = swl
        self.sdl = sdl
        self.downloadsubs = downloadsubs
        self.hearing_impaired = hearing_impaired
        self.subproviders = providers
        self.embedsubs = embedsubs
        self.embedonlyinternalsubs = embedonlyinternalsubs
        self.subencoding = subencoding

        # Import settings
        if settings is not None:
            self.importSettings(settings)
        self.deletesubs = set()
        self.converter = Converter(self.FFMPEG_PATH, self.FFPROBE_PATH)

    def importSettings(self, settings):
        self.FFMPEG_PATH = settings.ffmpeg
        self.FFPROBE_PATH = settings.ffprobe
        self.threads = settings.threads
        self.delete = settings.delete
        self.output_extension = settings.output_extension
        self.temp_extension = settings.temp_extension
        self.output_format = settings.output_format
        self.output_dir = settings.output_dir
        self.relocate_moov = settings.relocate_moov
        self.process_same_extensions = settings.process_same_extensions
        self.forceConvert = settings.forceConvert
        self.copyto = settings.copyto
        self.moveto = settings.moveto
        self.relocate_moov = settings.relocate_moov
        self.permissions = settings.permissions
        self.preopts = settings.preopts
        self.postopts = settings.postopts
        self.sort_streams = settings.sort_streams
        # Video settings
        self.video_codec = settings.vcodec
        self.video_bitrate = settings.vbitrate
        self.vcrf = settings.vcrf
        self.video_width = settings.vwidth
        self.video_profile = settings.vprofile
        self.h264_level = settings.h264_level
        self.qsv_decoder = settings.qsv_decoder
        self.hevc_qsv_decoder = settings.hevc_qsv_decoder
        self.dxva2_decoder = settings.dxva2_decoder
        self.pix_fmt = settings.pix_fmt
        # Audio settings
        self.audio_codec = settings.acodec
        self.audio_bitrate = settings.abitrate
        self.audio_filter = settings.afilter
        self.iOS = settings.iOS
        self.iOSFirst = settings.iOSFirst
        self.iOSLast = settings.iOSLast
        self.iOS_filter = settings.iOSfilter
        self.maxchannels = settings.maxchannels
        self.awl = settings.awl
        self.adl = settings.adl
        self.ignore_truehd = settings.ignore_truehd
        self.aac_adtstoasc = settings.aac_adtstoasc
        self.audio_copyoriginal = settings.audio_copyoriginal
        self.audio_first_language_track = settings.audio_first_language_track
        self.allow_language_relax = settings.allow_language_relax
        self.prefer_more_channels = settings.prefer_more_channels
        # Subtitle settings
        self.scodec = settings.scodec
        self.scodec_image = settings.scodec_image
        self.swl = settings.swl
        self.sdl = settings.sdl
        self.downloadsubs = settings.downloadsubs
        self.hearing_impaired = settings.hearing_impaired
        self.subproviders = settings.subproviders
        self.embedsubs = settings.embedsubs
        self.embedonlyinternalsubs = settings.embedonlyinternalsubs
        self.subencoding = settings.subencoding

        self.log.debug("Settings imported.")

    # Process a file from start to finish, with checking to make sure formats are compatible with selected settings
    def process(self, inputfile, reportProgress=False, original=None, info=None):
        self.log.debug("Process started.")

        delete = self.delete
        deleted = False
        options = None
        preopts = None
        postopts = None

        info = self.isValidSource(inputfile) if not info else info

        if info:
            options, preopts, postopts, ripsubopts = self.generateOptions(inputfile, info=info, original=original)
            if not options:
                self.log.error("Error converting, inputfile %s had a valid extension but returned no data. Either the file does not exist, was unreadable, or was an incorrect format." % inputfile)
                return False

            try:
                self.log.info("Output Data")
                self.log.info(json.dumps(options, sort_keys=False, indent=4))
                self.log.info("Preopts")
                self.log.info(json.dumps(preopts, sort_keys=False, indent=4))
                self.log.info("Postopts")
                self.log.info(json.dumps(postopts, sort_keys=False, indent=4))
                if not self.embedsubs:
                    self.log.info("Subtitle Extracts")
                    self.log.info(json.dumps(ripsubopts, sort_keys=False, indent=4))
            except:
                self.log.exception("Unable to log options.")

            self.ripSubs(inputfile, ripsubopts)

            outputfile, inputfile = self.convert(inputfile, options, preopts, postopts, reportProgress)

            if not outputfile:
                self.log.debug("Error converting, no outputfile generated for inputfile %s." % inputfile)
                return False

            self.log.debug("%s created from %s successfully." % (outputfile, inputfile))

            if outputfile == inputfile:
                self.deletesubs = set()
                if self.output_dir is not None:
                    try:
                        outputfile = os.path.join(self.output_dir, os.path.split(inputfile)[1])
                        self.log.debug("Outputfile set to %s." % outputfile)
                        shutil.copy(inputfile, outputfile)
                    except:
                        self.log.exception("Error moving file to output directory.")
                        delete = False
                else:
                    delete = False

            if delete:
                self.log.debug("Attempting to remove %s." % inputfile)
                if self.removeFile(inputfile):
                    self.log.debug("%s deleted." % inputfile)
                    deleted = True
                else:
                    self.log.error("Couldn't delete %s." % inputfile)

                for subfile in self.deletesubs:
                    self.log.debug("Attempting to remove subtitle %s." % subfile)
                    if self.removeFile(subfile):
                        self.log.debug("Subtitle %s deleted." % subfile)
                    else:
                        self.log.debug("Unable to delete subtitle %s." % subfile)
                self.deletesubs = set()

            dim = self.getDimensions(outputfile)
            input_extension = self.parseFile(inputfile)[2].lower()
            output_extension = self.parseFile(outputfile)[2].lower()

            return {'input': inputfile,
                    'input_extension': input_extension,
                    'input_deleted': deleted,
                    'output': outputfile,
                    'output_extension': output_extension,
                    'options': options,
                    'preopts': preopts,
                    'postopts': postopts,
                    'x': dim['x'],
                    'y': dim['y']}
        return None

    # Determine if a file can be read by FFPROBE
    def isValidSource(self, inputfile):
        info = self.converter.probe(inputfile)
        if info and not info.video:
            return None
        return info

    def isValidSubtitleSource(self, inputfile):
        info = self.converter.probe(inputfile)
        if info:
            if len(info.subtitle) < 1 or info.video or len(info.audio) > 0:
                return None
        return info

    # Get values for width and height to be passed to the tagging classes for proper HD tags
    def getDimensions(self, inputfile):
        info = self.converter.probe(inputfile)

        if info:
            self.log.debug("Height: %s" % info.video.video_height)
            self.log.debug("Width: %s" % info.video.video_width)

            return {'y': info.video.video_height,
                    'x': info.video.video_width}

        return {'y': 0,
                'x': 0}

    # Estimate the video bitrate
    def estimateVideoBitrate(self, info):
        total_bitrate = info.format.bitrate
        audio_bitrate = 0
        for a in info.audio:
            audio_bitrate += a.bitrate

        self.log.debug("Total bitrate is %s." % info.format.bitrate)
        self.log.debug("Total audio bitrate is %s." % audio_bitrate)
        self.log.debug("Estimated video bitrate is %s." % (total_bitrate - audio_bitrate))
        return ((total_bitrate - audio_bitrate) / 1000) * .95

    # Generate a JSON formatter dataset with the input and output information and ffmpeg command for a theoretical conversion
    def jsonDump(self, inputfile, original=None):
        dump = {}
        dump["input"] = self.generateSourceDict(inputfile)
        dump["output"], dump["preopts"], dump["postopts"], dump["ripsubopts"] = self.generateOptions(inputfile, original)
        parsed = self.converter.parse_options(dump["output"])
        input_dir, filename, input_extension = self.parseFile(inputfile)
        outputfile, output_extension = self.getOutputFile(input_dir, filename, input_extension)
        cmds = self.converter.ffmpeg.generateCommands(inputfile, outputfile, parsed, dump["preopts"], dump["postopts"])
        dump["ffmpeg_commands"] = []
        dump["ffmpeg_commands"].append(" ".join(str(item) for item in cmds))
        for suboptions in dump["ripsubopts"]:
            print(suboptions)
            subparsed = self.converter.parse_options(suboptions)
            extension = self.getSubExtensionFromCodec(suboptions['format'])
            suboutputfile = self.getSubOutputFileFromOptions(inputfile, suboptions, extension)
            subcmds = self.converter.ffmpeg.generateCommands(inputfile, suboutputfile, subparsed)
            dump["ffmpeg_commands"].append(" ".join(str(item) for item in subcmds))

        return json.dumps(dump, sort_keys=False, indent=4)

    # Generate a dict of data about a source file
    def generateSourceDict(self, inputfile):
        output = {}
        input_dir, filename, input_extension = self.parseFile(inputfile)
        output['extension'] = input_extension
        probe = self.converter.probe(inputfile)
        if probe:
            output.update(probe.toJson())
        else:
            output['error'] = "Invalid input, unable to read"
        return output

    # Pass over audio and subtitle streams to ensure the language properties are safe
    def safeLanguage(self, info):
        overrideLang = (self.awl is not None)

        # Loop through audio streams and clean up language metadata by standardizing undefined languages and applying the ADL setting
        for a in info.audio:
            try:
                if a.metadata['language'].strip() == "" or a.metadata['language'] is None:
                    a.metadata['language'] = 'und'
            except KeyError:
                a.metadata['language'] = 'und'

            # Set undefined language to default language if specified
            if self.adl is not None and a.metadata['language'] == 'und':
                self.log.debug("Undefined language detected, defaulting to %s." % self.adl)
                a.metadata['language'] = self.adl

            if (self.awl and a.metadata['language'].lower() in self.awl):
                overrideLang = False

        if overrideLang and self.allow_language_relax:
            self.awl = None
            self.log.info("No audio streams detected in any appropriate language, relaxing restrictions [allow-audio-language-relax].")

        # Prep subtitle streams by cleaning up languages and setting SDL
        for s in info.subtitle:
            try:
                if s.metadata['language'] == "" or s.metadata['language'] is None:
                    s.metadata['language'] = 'und'
            except KeyError:
                s.metadata['language'] = 'und'

            # Set undefined language to default language if specified
            if self.sdl is not None and s.metadata['language'] == 'und':
                self.log.debug("Undefined language detected, defaulting to [%s]." % self.sdl)
                s.metadata['language'] = self.sdl

    # Generate a dict of options to be passed to FFMPEG based on selected settings and the source file parameters and streams
    def generateOptions(self, inputfile, info=None, original=None):
        # Get path information from the input file
        input_dir, filename, input_extension = self.parseFile(inputfile)

        ripsubopts = []

        info = self.converter.probe(inputfile) if not info else info

        if not info:
            self.log.error("FFProbe returned no value for inputfile %s (exists: %s), either the file does not exist or is not a format FFPROBE can read." % (inputfile, os.path.exists(inputfile)))
            return None, None, None, None

        self.safeLanguage(info)

        try:
            self.log.info("Input Data")
            self.log.info(json.dumps(info.toJson(), sort_keys=False, indent=4))
        except:
            self.log.exception("Unable to print input file data")
        # Video stream
        self.log.info("Reading video stream.")
        self.log.info("Video codec detected: %s." % info.video.codec)

        vdebug = "base"
        try:
            vbr = self.estimateVideoBitrate(info)
        except:
            vbr = info.format.bitrate / 1000

        if info.video.codec.lower() in self.video_codec:
            vcodec = 'copy'
        else:
            vcodec = self.video_codec[0]
        vbitrate = self.video_bitrate if self.video_bitrate else vbr

        self.log.info("Pix Fmt: %s." % info.video.pix_fmt)
        if self.pix_fmt and info.video.pix_fmt.lower() not in self.pix_fmt:
            self.log.debug("Overriding video pix_fmt. Codec cannot be copied because pix_fmt is not approved.")
            vdebug = vdebug + ".pix_fmt"
            vcodec = self.video_codec[0]
            pix_fmt = self.pix_fmt[0]
            if self.video_profile:
                vprofile = self.video_profile[0]
        elif self.pix_fmt:
            pix_fmt = self.pix_fmt[0]
        else:
            pix_fmt = None

        if self.video_bitrate is not None and vbr > self.video_bitrate:
            self.log.debug("Overriding video bitrate. Codec cannot be copied because video bitrate is too high.")
            vdebug = vdebug + ".video-bitrate"
            vcodec = self.video_codec[0]
            vbitrate = self.video_bitrate

        vwidth = self.video_width
        if self.video_width is not None and self.video_width < info.video.video_width:
            self.log.debug("Video width is over the max width, it will be downsampled. Video stream can no longer be copied.")
            vdebug = vdebug + ".video-max-width"
            vcodec = self.video_codec[0]

        if '264' in info.video.codec.lower() and self.h264_level and info.video.video_level and (info.video.video_level / 10 > self.h264_level):
            self.log.info("Video level %0.1f. Codec cannot be copied because video level is too high." % (info.video.video_level / 10))
            vdebug = vdebug + ".h264-max-level"
            vcodec = self.video_codec[0]

        self.log.debug("Video codec: %s." % vcodec)
        self.log.debug("Video bitrate: %s." % vbitrate)

        self.log.info("Profile: %s." % info.video.profile)
        if self.video_profile and info.video.profile.lower().replace(" ", "") not in self.video_profile:
            self.log.debug("Video profile is not supported. Video stream can no longer be copied.")
            vdebug = vdebug + ".video-profile"
            vcodec = self.video_codec[0]
            vprofile = self.video_profile[0]
            if self.pix_fmt:
                pix_fmt = self.pix_fmt[0]
        elif self.video_profile:
            vprofile = self.video_profile[0]
        else:
            vprofile = None

        # Audio streams
        self.log.info("Reading audio streams.")

        # Reorder audio streams based on the approved audio languages and channels
        audio_streams = info.audio
        if self.sort_streams:
            self.log.debug("Reordering audio streams to be in accordance with approved languages and channels [sort-streams, prefer-more-channels].")
            audio_streams.sort(key=lambda x: x.audio_channels, reverse=self.prefer_more_channels)
            if self.awl:
                audio_streams.sort(key=lambda x: self.awl.index(x.metadata['language']) if x.metadata['language'] in self.awl else 999)

        # Iterate through audio streams
        audio_settings = {}
        blocked_audio_languages = []
        l = 0
        for a in audio_streams:
            self.log.info("Audio detected for stream %s - %s %s %d channel." % (a.index, a.codec, a.metadata['language'], a.audio_channels))

            if self.output_extension in valid_tagging_extensions and a.codec.lower() == 'truehd' and self.ignore_truehd:
                if len(info.audio) > 1:
                    self.log.info("Skipping trueHD stream %s as typically the 2nd audio stream is the AC3 core of the truehd stream [ignore-truehd]." % a.index)
                    continue
                else:
                    self.log.info("TrueHD stream detected but no other audio streams in source, cannot skip stream %s [ignore-truehd]." % a.index)

            # Proceed if no whitelist is set, or if the language is in the whitelist
            iosdata = None
            if self.awl is None or (a.metadata['language'].lower() in self.awl and a.metadata['language'].lower() not in blocked_audio_languages):
                # Create iOS friendly audio stream if the default audio stream has too many channels (iOS only likes AAC stereo)
                if self.iOS and a.audio_channels > 2:
                    iOSbitrate = 256 if (self.audio_bitrate * 2) > 256 else (self.audio_bitrate * 2)

                    # Bitrate calculations/overrides
                    if self.audio_bitrate is 0:
                        self.log.debug("Attempting to set ios stream bitrate based on source stream bitrate.")
                        try:
                            iOSbitrate = ((a.bitrate / 1000) / a.audio_channels) * 2
                        except:
                            self.log.warning("Unable to determine iOS audio bitrate from source stream %s, defaulting to 128 per channel." % a.index)
                            iOSbitrate = 2 * 128

                    iosdisposition = '+default' if a.default else ''

                    self.log.debug("Audio codec: %s." % self.iOS[0])
                    self.log.debug("Channels: 2.")
                    self.log.debug("Filter: %s." % self.iOS_filter)
                    self.log.debug("Bitrate: %s." % iOSbitrate)
                    self.log.debug("Language: %s." % a.metadata['language'])
                    self.log.debug("Disposition: %s." % iosdisposition)

                    iosdata = {
                        'map': a.index,
                        'codec': self.iOS[0],
                        'channels': 2,
                        'bitrate': iOSbitrate,
                        'filter': self.iOS_filter,
                        'language': a.metadata['language'],
                        'disposition': iosdisposition,
                        'debug': 'ios-audio'
                    }
                    if not self.iOSLast:
                        self.log.info("Creating %s audio stream %d from source audio stream %d [iOS-audio]." % (self.iOS[0], l, a.index))
                        audio_settings.update({l: iosdata})
                        l += 1

                adebug = "base"
                # If the iOS audio option is enabled and the source audio channel is only stereo, the additional iOS channel will be skipped and a single AAC 2.0 channel will be made regardless of codec preference to avoid multiple stereo channels
                if self.iOS and a.audio_channels <= 2:
                    self.log.debug("Overriding default channel settings because iOS audio is enabled but the source is stereo [iOS-audio].")
                    acodec = 'copy' if a.codec in self.iOS else self.iOS[0]
                    audio_channels = a.audio_channels
                    afilter = self.iOS_filter
                    abitrate = a.audio_channels * 128 if (a.audio_channels * self.audio_bitrate) > (a.audio_channels * 128) else (a.audio_channels * self.audio_bitrate)
                    adebug = adebug + ".ios-audio"
                else:
                    # If desired codec is the same as the source codec, copy to avoid quality loss
                    acodec = 'copy' if a.codec.lower() in self.audio_codec else self.audio_codec[0]
                    afilter = self.audio_filter
                    # Audio channel adjustments
                    if self.maxchannels and a.audio_channels > self.maxchannels:
                        self.log.debug("Audio source exceeds maximum channels, can not be copied. Settings channels to %d [audio-max-channels]." % self.maxchannels)
                        adebug = adebug + ".audio-max-channels"
                        audio_channels = self.maxchannels
                        acodec = self.audio_codec[0]
                        abitrate = self.maxchannels * self.audio_bitrate
                    else:
                        audio_channels = a.audio_channels
                        abitrate = a.audio_channels * self.audio_bitrate

                # Bitrate calculations/overrides
                if self.audio_bitrate is 0:
                    self.log.debug("Attempting to set bitrate based on source stream bitrate.")
                    try:
                        abitrate = ((a.bitrate / 1000) / a.audio_channels) * audio_channels
                    except:
                        self.log.warning("Unable to determine audio bitrate from source stream %s, defaulting to 256 per channel." % a.index)
                        abitrate = audio_channels * 256

                adisposition = '+default' if a.default else ''

                self.log.debug("Audio codec: %s." % acodec)
                self.log.debug("Channels: %s." % audio_channels)
                self.log.debug("Bitrate: %s." % abitrate)
                self.log.debug("Language: %s" % a.metadata['language'])
                self.log.debug("Filter: %s" % afilter)
                self.log.debug("Disposition: %s" % adisposition)
                self.log.debug("Debug: %s" % adebug)

                # If the iOSFirst option is enabled, disable the iOS option after the first audio stream is processed
                if self.iOS and self.iOSFirst:
                    self.log.debug("Not creating any additional iOS audio streams [iOS-first-track-only].")
                    self.iOS = False

                self.log.info("Creating %s audio stream %d from source stream %d." % (acodec, l, a.index))
                audio_settings.update({l: {
                    'map': a.index,
                    'codec': acodec,
                    'channels': audio_channels,
                    'bitrate': abitrate,
                    'filter': afilter,
                    'language': a.metadata['language'],
                    'disposition': adisposition,
                    'debug': adebug
                }})

                if acodec == 'copy' and a.codec == 'aac' and self.aac_adtstoasc:
                    audio_settings[l]['bsf'] = 'aac_adtstoasc'
                l += 1

                # Add the iOS stream last instead
                if self.iOSLast and iosdata:
                    self.log.info("Creating %s audio stream %d from source audio stream %d [iOS-audio]." % (self.iOS[0], l, a.index))
                    audio_settings.update({l: iosdata})
                    l += 1

                if self.audio_copyoriginal and acodec != 'copy' and not (a.codec.lower() == 'truehd' and self.ignore_truehd):
                    self.log.info("Copying to audio stream %d from source stream %d format %s [audio-copy-original]." % (l, a.index, a.codec))
                    audio_settings.update({l: {
                        'map': a.index,
                        'codec': 'copy',
                        'channels': a.audio_channels,
                        'language': a.metadata['language'],
                        'disposition': adisposition,
                        'debug': 'audio-copy-original'
                    }})
                    l += 1

                # Remove the language if we only want the first stream from a given language
                if self.audio_first_language_track:
                    try:
                        blocked_audio_languages.append(a.metadata['language'].lower())
                        self.log.debug("Removing language from whitelist to prevent multiple streams of the same: %s [audio-first-track-of-language]." % a.metadata['language'])
                    except:
                        self.log.error("Unable to remove language %s from whitelist [audio-first-track-of-language]." % a.metadata['language'])

        # Audio Default Handler
        if len(audio_settings) > 0:
            audio_streams = sorted(audio_settings.values(), key=lambda x: x['channels'], reverse=self.prefer_more_channels)
            preferred_language_audio_streams = [x for x in audio_streams if x['language'] == self.adl] if self.adl else audio_streams
            default_stream = audio_streams[0]
            default_streams = [x for x in audio_streams if 'default' in x['disposition']]
            default_preferred_language_streams = [x for x in default_streams if x['language'] == self.adl] if self.adl else default_streams
            default_streams_not_in_preferred_language = [x for x in default_streams if x not in default_preferred_language_streams]

            self.log.debug("%d total audio streams with %d set to default disposition. %d defaults in your preferred language (%s), %d in other languages." % (len(audio_streams), len(default_streams), len(default_preferred_language_streams), self.adl, len(default_streams_not_in_preferred_language)))
            if len(preferred_language_audio_streams) < 1:
                self.log.debug("No audio tracks in your preferred language, using other languages to determine default stream.")

            if len(default_preferred_language_streams) < 1:
                try:
                    potential_streams = preferred_language_audio_streams if len(preferred_language_audio_streams) > 0 else default_streams
                    default_stream = potential_streams[0] if len(potential_streams) > 0 else audio_streams[0]
                except:
                    self.log.exception("Error setting default stream in preferred language.")
            elif len(default_preferred_language_streams) > 1:
                default_stream = default_preferred_language_streams[0]
                try:
                    for remove in default_preferred_language_streams[1:]:
                        remove['disposition'] = remove['disposition'].replace("+default", "")
                    self.log.debug("%d streams in preferred language cleared of default disposition flag from preferred language." % (len(default_preferred_language_streams) - 1))
                except:
                    self.log.exception("Error in removing default disposition flag from extra audio streams, multiple streams may be set as default.")
            else:
                self.log.debug("Default audio stream already inherited from source material, will not override to audio-language-default.")
                default_stream = default_preferred_language_streams[0]

            default_streams_not_in_preferred_language = [x for x in default_streams_not_in_preferred_language if x != default_stream]
            if len(default_streams_not_in_preferred_language) > 0:
                self.log.debug("Cleaning up default disposition settings from not preferred languages. %d streams will have default flag removed." % (len(default_streams_not_in_preferred_language)))
                for remove in default_streams_not_in_preferred_language:
                    remove['disposition'] = remove['disposition'].replace("+default", "")

            try:
                if 'default' not in default_stream['disposition']:
                    default_stream['disposition'] += "+default"
            except:
                default_stream['disposition'] = "+default"
            self.log.info("Default audio stream set to %s %s %s channel stream [prefer-more-channels: %s]." % (default_stream['language'], default_stream['codec'], default_stream['channels'], self.prefer_more_channels))
        else:
            self.log.debug("Audio output is empty, unable to set default audio streams.")

        # Reorder subtitle streams based on the approved languages, mirrors the order present from the options
        subtitle_streams = info.subtitle
        if self.sort_streams and self.swl:
            self.log.debug("Reordering subtitle streams to be in accordance with approved languages [sort-streams].")
            subtitle_streams.sort(key=lambda x: self.swl.index(x.metadata['language']) if x.metadata['language'] in self.swl else 999)

        # Iterate through subtitle streams
        subtitle_settings = {}
        l = 0
        self.log.info("Reading subtitle streams.")
        for s in subtitle_streams:
            image_based = self.isImageBasedSubtitle(inputfile, s.index)
            self.log.info("%s-based subtitle detected for stream %s - %s %s." % ("Image" if image_based else "Text", s.index, s.codec, s.metadata['language']))

            scodec = None
            if image_based and self.scodec_image and len(self.scodec_image) > 0:
                scodec = self.scodec_image[0]
            elif not image_based and self.scodec and len(self.scodec) > 0:
                scodec = self.scodec[0]

            if self.embedsubs and scodec:
                # Proceed if no whitelist is set, or if the language is in the whitelist
                if self.swl is None or s.metadata['language'].lower() in self.swl:
                    disposition = ''
                    if s.default:
                        disposition += '+default'
                    if s.forced:
                        disposition += '+forced'

                    subtitle_settings.update({l: {
                        'map': s.index,
                        'codec': scodec,
                        'language': s.metadata['language'],
                        'encoding': self.subencoding,
                        'disposition': disposition,
                        'debug': 'base.embed-subs'
                    }})
                    self.log.info("Creating %s subtitle stream %d from source stream %d." % (self.scodec[0], l, s.index))
                    l = l + 1
            elif not self.embedsubs:
                if self.swl is None or s.metadata['language'].lower() in self.swl:
                    for codec in (self.scodec_image if image_based else self.scodec):
                        ripsub = {0: {
                            'map': s.index,
                            'codec': codec,
                            'language': s.metadata['language'],
                            'debug': "base"
                        }}
                        options = {
                            'format': codec,
                            'subtitle': ripsub,
                            'forced': s.forced,
                            'default': s.default,
                            'language': s.metadata['language'],
                            'index': s.index
                        }
                        ripsubopts.append(options)

        # Attempt to download subtitles if they are missing using subliminal
        if self.downloadsubs:
            self.downloadSubtitles(inputfile, info.subtitle, original)

        # External subtitle import
        if self.embedsubs and not self.embedonlyinternalsubs:  # Don't bother if we're not embeddeding subtitles and external subtitles
            src = 1  # FFMPEG input source number
            for dirName, subdirList, fileList in os.walk(input_dir):
                for fname in fileList:
                    subname, subextension = os.path.splitext(fname)
                    # Watch for appropriate file extension
                    external_info = self.isValidSubtitleSource(os.path.join(dirName, fname))
                    if external_info:
                        x, lang = os.path.splitext(subname)
                        while '.forced' in lang or '.default' in lang:
                            x, lang = os.path.splitext(x)
                        lang = lang[1:]
                        # Using bablefish to convert a 2 language code to a 3 language code
                        if len(lang) is 2:
                            try:
                                babel = Language.fromalpha2(lang)
                                lang = babel.alpha3
                            except:
                                pass
                        # If subtitle file name and input video name are the same, proceed
                        if filename in fname:
                            self.log.info("External %s subtitle file detected." % lang)
                            if self.swl is None or lang in self.swl:
                                disposition = ''
                                if ".default" in fname:
                                    disposition += '+default'
                                if ".forced" in fname:
                                    disposition += '+forced'
                                image_based = self.isImageBasedSubtitle(os.path.join(dirName, fname), 0)
                                scodec = None
                                if image_based and self.scodec_image and len(self.scodec_image) > 0:
                                    scodec = self.scodec_image[0]
                                elif not image_based and self.scodec and len(self.scodec) > 0:
                                    scodec = self.scodec[0]

                                if not scodec:
                                    self.log.debug("Skipping external subtitle file %s, no appropriate codecs found." % fname)
                                    continue

                                self.log.info("Creating subtitle stream %s by importing %s-based %s [embed-subs]." % (l, "Image" if image_based else "Text", fname))

                                subtitle_settings.update({l: {
                                    'path': os.path.join(dirName, fname),
                                    'source': src,
                                    'map': 0,
                                    'codec': scodec,
                                    'disposition': disposition,
                                    'language': lang,
                                    'debug': 'base.embed-subs'}})

                                self.log.debug("Path: %s." % os.path.join(dirName, fname))
                                self.log.debug("Source: %s." % src)
                                self.log.debug("Codec: %s." % self.scodec[0])
                                self.log.debug("Langauge: %s." % lang)
                                self.log.debug("Disposition: %s." % disposition)

                                l = l + 1
                                src = src + 1

                                self.deletesubs.add(os.path.join(dirName, fname))

                            else:
                                self.log.info("Ignoring %s external subtitle stream due to language %s." % (fname, lang))

        # Subtitle Default
        if len(subtitle_settings) > 0 and self.sdl:
            if len([x for x in subtitle_settings.values() if 'default' in x['disposition']]) < 1:
                try:
                    default_stream = [x for x in subtitle_settings.values() if x['language'] == self.sdl][0]
                    default_stream['disposition'] = '+default'
                except:
                    subtitle_settings[0]['disposition'] = '+default'
            else:
                self.log.debug("Default subtitle stream already inherited from source material, will not override to subtitle-language-default.")
        else:
            self.log.debug("Subtitle output is empty or no default subtitle language is set, will not pass over subtitle output to set a default stream.")

        # Collect all options
        options = {
            'format': self.output_format,
            'video': {
                'codec': vcodec,
                'map': info.video.index,
                'bitrate': vbitrate,
                'level': self.h264_level,
                'profile': vprofile,
                'pix_fmt': pix_fmt,
                'field_order': info.video.field_order,
                'width': vwidth,
                'debug': vdebug,
            },
            'audio': audio_settings,
            'subtitle': subtitle_settings
        }

        preopts = []
        postopts = ['-threads', self.threads]

        # If a CRF option is set, override the determine bitrate
        if self.vcrf:
            del options['video']['bitrate']
            options['video']['crf'] = self.vcrf

        if len(options['subtitle']) > 0:
            preopts.append('-fix_sub_duration')

        if self.preopts:
            preopts.extend(self.preopts)

        if self.postopts:
            postopts.extend(self.postopts)

        if self.dxva2_decoder:  # DXVA2 will fallback to CPU decoding when it hits a file that it cannot handle, so we don't need to check if the file is supported.
            preopts.extend(['-hwaccel', 'dxva2'])
        elif info.video.codec.lower() == "hevc" and self.hevc_qsv_decoder:
            preopts.extend(['-vcodec', 'hevc_qsv'])
        elif vcodec == "h264qsv" and info.video.codec.lower() == "h264" and self.qsv_decoder and (info.video.video_level / 10) < 5:
            preopts.extend(['-vcodec', 'h264_qsv'])

        # HEVC Tagging for copied streams
        if info.video.codec.lower() in ['x265', 'h265', 'hevc'] and vcodec == 'copy':
            postopts.extend(['-tag:v', 'hvc1'])
            self.log.info("Tagging copied video stream as hvc1")

        return options, preopts, postopts, ripsubopts

    def downloadSubtitles(self, inputfile, existing_subtitle_tracks, original=None):
        try:
            self.log.debug(subliminal.__version__)
        except:
            self.log.error("Subliminal is not installed, downloading subtitles aborted.")
            return

        languages = set()
        if self.swl:
            for alpha3 in self.swl:
                try:
                    languages.add(Language(alpha3))
                except:
                    self.log.exception("Unable to add language for download with subliminal.")
        if self.sdl:
            try:
                languages.add(Language(self.sdl))
            except:
                self.log.exception("Unable to add language for download with subliminal.")

        if len(languages) < 1:
            self.log.error("No valid subtitle download languages detected, subtitles will not be downloaded.")
            return

        self.log.info("Attempting to download subtitles.")

        # Attempt to set the dogpile cache
        try:
            subliminal.region.configure('dogpile.cache.memory')
        except:
            pass

        try:
            video = subliminal.scan_video(os.path.abspath(inputfile))
            video.subtitle_languages = set([Language(x.metadata['language']) for x in existing_subtitle_tracks])

            # If data about the original release is available, include that in the search to best chance at accurate subtitles
            if original:
                og = subliminal.Video.fromname(original)
                video.format = og.format
                video.release_group = og.release_group
                video.resolution = og.resolution

            subtitles = subliminal.download_best_subtitles([video], languages, hearing_impaired=self.hearing_impaired, providers=self.subproviders)
            saves = subliminal.save_subtitles(video, subtitles[video])
            paths = [subliminal.subtitle.get_subtitle_path(video.name, x.language) for x in saves]
            for path in paths:
                self.log.info("Downloaded new subtitle %s." % path)
                self.setPermissions(path)

            return paths
        except:
            self.log.exception("Unable to download subtitles.")
            return None

    def setPermissions(self, path):
        try:
            os.chmod(path, self.permissions.get('chmod', int('0755', 8)))
            if os.name != 'nt':
                os.chown(path, self.permissions.get('uid', -1), self.permissions.get('gid', -1))
        except:
            self.log.exception("Unable to set new file permissions.")

    def getSubExtensionFromCodec(self, codec):
        try:
            return subtitle_codec_extensions[codec]
        except:
            self.log.info("Wasn't able to determine subtitle file extension, defaulting to codec %s." % codec)
            return codec

    def getSubOutputFileFromOptions(self, inputfile, options, extension):
        language = options["language"]
        return self.getSubOutputFile(inputfile, language, options['forced'], options['default'], extension)

    def getSubOutputFile(self, inputfile, language, forced, default, extension):
        forced = ".forced" if forced else ""
        default = ".default" if default else ""
        input_dir, filename, input_extension = self.parseFile(inputfile)
        output_dir = input_dir if self.output_dir is None else self.output_dir
        outputfile = os.path.join(output_dir, filename + "." + language + default + forced + "." + extension)

        i = 2
        while os.path.isfile(outputfile):
            self.log.debug("%s exists, appending %s to filename." % (outputfile, i))
            outputfile = os.path.join(output_dir, filename + "." + language + default + forced + "." + str(i) + "." + extension)
            i += 1
        return outputfile

    def ripSubs(self, inputfile, ripsubopts):
        for options in ripsubopts:
            extension = self.getSubExtensionFromCodec(options['format'])
            outputfile = self.getSubOutputFileFromOptions(inputfile, options, extension)

            try:
                self.log.info("Ripping %s subtitle from source stream %s into external file." % (options["language"], options['index']))
                conv = self.converter.convert(inputfile, outputfile, options, timeout=None)
                for timecode in conv:
                    pass

                self.log.info("%s created." % outputfile)
            except (FFMpegConvertError, ConverterError):
                self.log.error("Unable to create external %s subtitle file for stream %s, may be an incompatible format." % (extension, options['index']))
                self.removeFile(outputfile)
                continue
            except:
                self.log.exception("Unable to create external subtitle file for stream %s." % (options['index']))
            self.setPermissions(outputfile)

    def getOutputFile(self, input_dir, filename, input_extension, temp_extension=None, number=0):
        output_dir = input_dir if self.output_dir is None else self.output_dir
        output_extension = temp_extension if temp_extension else self.output_extension

        self.log.debug("Input directory: %s." % input_dir)
        self.log.debug("File name: %s." % filename)
        self.log.debug("Input extension: %s." % input_extension)
        self.log.debug("Output directory: %s." % output_dir)
        self.log.debug("Output extension: %s." % output_dir)

        counter = ("(%d)" % number) if number > 0 else ""

        try:
            outputfile = os.path.join(output_dir.decode(sys.getfilesystemencoding()), filename.decode(sys.getfilesystemencoding()) + counter + "." + output_extension).encode(sys.getfilesystemencoding())
        except:
            outputfile = os.path.join(output_dir, filename + counter + "." + output_extension)

        self.log.debug("Output file: %s." % outputfile)
        return outputfile, output_dir

    def isImageBasedSubtitle(self, inputfile, map):
        outputfile = self.getSubOutputFile(inputfile, "null", False, False, "subtest")
        ripsub = {0: {'map': map, 'codec': 'srt'}}
        options = {'format': 'srt', 'subtitle': ripsub}
        try:
            conv = self.converter.convert(inputfile, outputfile, options, timeout=30)
            for timecode in conv:
                pass
        except FFMpegConvertError:
            self.removeFile(outputfile)
            return True
        except:
            self.log.exception("Unknown error when trying to determine if subtitle is image based.")
            self.removeFile(outputfile)
            return True
        self.removeFile(outputfile)
        return False

    def canBypassConvert(self, input_extension, options):
        # Process same extensions
        if self.output_extension == input_extension:
            if not self.forceConvert and not self.process_same_extensions:
                self.log.info("Input and output extensions are the same so passing back the original file [process-same-extensions: %s]." % self.process_same_extensions)
                return True
            # Force convert
            elif not self.forceConvert and len([x for x in [options['video']] + [x for x in options['audio'].values()] + [x for x in options['subtitle'].values()] if x['codec'] != 'copy']) == 0:
                self.log.info("Input and output extensions match and every codec is copy, this file probably doesn't need conversion, returning [force-convert: %s]." % self.forceConvert)
                return True
            elif self.forceConvert:
                self.log.info("Input and output extensions match and every codec is copy, this file probably doesn't need conversion, but conversion being forced [force-convert: %s]." % self.forceConvert)
        return False

    # Encode a new file based on selected options, built in naming conflict resolution
    def convert(self, inputfile, options, preopts, postopts, reportProgress=False):
        self.log.info("Starting conversion.")
        input_dir, filename, input_extension = self.parseFile(inputfile)
        originalinputfile = inputfile
        outputfile, output_dir = self.getOutputFile(input_dir, filename, input_extension, self.temp_extension)
        finaloutputfile, _ = self.getOutputFile(input_dir, filename, input_extension)

        self.log.debug("Final output file: %s." % finaloutputfile)

        if len(options['audio']) == 0:
            self.error.info("Conversion has no audio streams, aborting")
            return None, inputfile

        if self.canBypassConvert(input_extension, options):
            return inputfile, inputfile

        # Check if input file and the final output file are the same and preferentially rename files (input first, then output if that fails)
        if os.path.abspath(inputfile) == os.path.abspath(finaloutputfile):
            self.log.debug("Inputfile and final outputfile are the same, trying to rename inputfile first.")
            try:
                og = inputfile + ".original"
                i = 2
                while os.path.isfile(og):
                    og = og + "2"
                    i += 1
                os.rename(inputfile, og)
                inputfile = og
                self.log.debug("Renamed original file to %s." % inputfile)
            except:
                i = 2
                while os.path.isfile(finaloutputfile):
                    outputfile, output_dir = self.getOutputFile(input_dir, filename, input_extension, self.temp_extension, number=i)
                    finaloutputfile, _ = self.getOutputFile(input_dir, filename, input_extension, number=i)
                    i += 1
                self.log.debug("Unable to rename inputfile. Alternatively renaming output file to %s." % outputfile)

        # Delete output file if it already exists and deleting enabled
        if os.path.exists(outputfile) and self.delete:
            self.removeFile(outputfile)

        # Final sweep to make sure outputfile does not exist, renaming as the final solution
        i = 2
        while os.path.isfile(outputfile):
            outputfile, output_dir = self.getOutputFile(input_dir, filename, input_extension, self.temp_extension, number=i)
            finaloutputfile, _ = self.getOutputFile(input_dir, filename, input_extension, number=i)
            i += 1

        conv = self.converter.convert(inputfile, outputfile, options, timeout=None, preopts=preopts, postopts=postopts)

        try:
            for timecode in conv:
                if reportProgress:
                    try:
                        sys.stdout.write('\r')
                        sys.stdout.write('[{0}] {1}%'.format('#' * (timecode / 10) + ' ' * (10 - (timecode / 10)), timecode))
                    except:
                        sys.stdout.write(str(timecode))
                    sys.stdout.flush()

            self.log.info("%s created." % outputfile)
            self.setPermissions(outputfile)

        except FFMpegConvertError as e:
            self.log.exception("Error converting file, FFMPEG error.")
            self.log.error(e.cmd)
            self.log.error(e.output)
            if os.path.isfile(outputfile):
                self.removeFile(outputfile)
                self.log.error("%s deleted." % outputfile)
            outputfile = None
            os.rename(inputfile, originalinputfile)
            raise Exception("FFMpegConvertError")

        # Check if the finaloutputfile differs from the outputfile. This can happen during above renaming or from temporary extension option
        if outputfile != finaloutputfile:
            self.log.debug("Outputfile and finaloutputfile are different attempting to rename to final extension [temp_extension].")
            try:
                os.rename(outputfile, finaloutputfile)
            except:
                self.log.exception("Unable to rename output file to its final destination file extension [temp_extension].")
                finaloutputfile = outputfile

        return finaloutputfile, inputfile

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
        if os.path.isfile(inputfile) and self.relocate_moov:
            from qtfaststart import processor, exceptions

            self.log.info("Relocating MOOV atom to start of file.")

            try:
                outputfile = inputfile.decode(sys.getfilesystemencoding()) + temp_ext
            except:
                outputfile = inputfile + temp_ext

            # Clear out the temp file if it exists
            if os.path.exists(outputfile):
                self.removeFile(outputfile, 0, 0)

            try:
                processor.process(inputfile, outputfile)
                self.setPermissions(outputfile)

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
        files = [inputfile]

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
                    files.append(os.path.join(d, os.path.split(inputfile)[1]))
                except:
                    self.log.exception("First attempt to copy the file has failed.")
                    try:
                        if os.path.exists(inputfile):
                            self.removeFile(inputfile, 0, 0)
                        try:
                            shutil.copy(inputfile.decode(sys.getfilesystemencoding()), d)
                        except:
                            shutil.copy(inputfile, d)
                        self.log.info("%s copied to %s." % (inputfile, d))
                        files.append(os.path.join(d, os.path.split(inputfile)[1]))
                    except:
                        self.log.exception("Unable to create additional copy of file in %s." % (d))

        if self.moveto:
            self.log.debug("Moveto option is enabled.")
            moveto = os.path.join(self.moveto, relativePath) if relativePath else self.moveto
            if not os.path.exists(moveto):
                os.makedirs(moveto)
            try:
                shutil.move(inputfile, moveto)
                self.log.info("%s moved to %s." % (inputfile, moveto))
                files[0] = os.path.join(moveto, os.path.basename(inputfile))
            except:
                self.log.exception("First attempt to move the file has failed.")
                try:
                    if os.path.exists(inputfile):
                        self.removeFile(inputfile, 0, 0)
                    shutil.move(inputfile.decode(sys.getfilesystemencoding()), moveto)
                    self.log.info("%s moved to %s." % (inputfile, moveto))
                    files[0] = os.path.join(moveto, os.path.basename(inputfile))
                except:
                    self.log.exception("Unable to move %s to %s" % (inputfile, moveto))
        for filename in files:
            self.log.debug("Final output file: %s." % filename)
        return files

    # Robust file removal function, with options to retry in the event the file is in use, and replace a deleted file
    def removeFile(self, filename, retries=2, delay=10, replacement=None):
        for i in range(retries + 1):
            try:
                # Make sure file isn't read-only
                os.chmod(filename, int("0777", 8))
            except:
                self.log.debug("Unable to set file permissions before deletion. This is not always required.")
            try:
                if os.path.exists(filename):
                    os.remove(filename)
                # Replaces the newly deleted file with another by renaming (replacing an original with a newly created file)
                if replacement is not None:
                    os.rename(replacement, filename)
                    filename = replacement
                break
            except:
                self.log.exception("Unable to remove or replace file %s." % filename)
                if delay > 0:
                    self.log.debug("Delaying for %s seconds before retrying." % delay)
                    time.sleep(delay)
        return False if os.path.isfile(filename) else True
