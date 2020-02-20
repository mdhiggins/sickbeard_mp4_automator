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
    log = logging.getLogger(__name__)
    deletesubs = set()

    def __init__(self, settings, logger=None):
        # Setup Logging
        if logger:
            self.log = logger
        self.settings = settings
        self.converter = Converter(settings.ffmpeg, settings.ffprobe)

    # Process a file from start to finish, with checking to make sure formats are compatible with selected settings
    def process(self, inputfile, reportProgress=False, original=None, info=None):
        self.log.debug("Process started.")

        delete = self.settings.delete
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
                if not self.settings.embedsubs:
                    self.log.info("Subtitle Extracts")
                    self.log.info(json.dumps(ripsubopts, sort_keys=False, indent=4))
            except:
                self.log.exception("Unable to log options.")

            self.ripSubs(inputfile, ripsubopts)

            outputfile, inputfile = self.convert(options, preopts, postopts, reportProgress)

            if not outputfile:
                self.log.debug("Error converting, no outputfile generated for inputfile %s." % inputfile)
                return False

            self.log.debug("%s created from %s successfully." % (outputfile, inputfile))

            if outputfile == inputfile:
                self.settings.deletesubs = set()
                if self.settings.output_dir is not None:
                    try:
                        outputfile = os.path.join(self.settings.output_dir, os.path.split(inputfile)[1])
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
        try:
            info = self.converter.probe(inputfile)
            if not info:
                self.log.debug("Invalid source, no data returned.")
                return None
            if not info.video:
                self.log.debug("Invalid source, no video stream detected")
                return None
            if not info.audio or len(info.audio) < 1:
                self.log.debug("Invalid source, no audio stream detected")
                return None
            return info
        except:
            self.log.exception("isValidSource unexpectedly threw an exception, returning None")
            return None

    def isValidSubtitleSource(self, inputfile):
        try:
            info = self.converter.probe(inputfile)
            if info:
                if len(info.subtitle) < 1 or info.video or len(info.audio) > 0:
                    return None
            return info
        except:
            self.log.exception("isValidSubtitleSource unexpectedly threw an exception, returning None")
            return None

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
        cmds = self.converter.ffmpeg.generateCommands(outputfile, parsed, dump["preopts"], dump["postopts"])
        dump["ffmpeg_commands"] = []
        dump["ffmpeg_commands"].append(" ".join(str(item) for item in cmds))
        for suboptions in dump["ripsubopts"]:
            subparsed = self.converter.parse_options(suboptions)
            extension = self.getSubExtensionFromCodec(suboptions['format'])
            suboutputfile = self.getSubOutputFileFromOptions(inputfile, suboptions, extension)
            subcmds = self.converter.ffmpeg.generateCommands(suboutputfile, subparsed)
            dump["ffmpeg_commands"].append(" ".join(str(item) for item in subcmds))

        return json.dumps(dump, sort_keys=False, indent=4)

    # Generate a dict of data about a source file
    def generateSourceDict(self, inputfile):
        output = {}
        input_dir, filename, input_extension = self.parseFile(inputfile)
        output['extension'] = input_extension
        probe = self.converter.probe(inputfile)
        if probe:
            output.update(probe.toJson)
        else:
            output['error'] = "Invalid input, unable to read"
        return output

    # Pass over audio and subtitle streams to ensure the language properties are safe, return any adjustments made to SWL/AWL if relax is enabled
    def safeLanguage(self, info):
        awl = self.settings.awl
        swl = self.settings.swl
        overrideLang = (awl is not None)

        # Loop through audio streams and clean up language metadata by standardizing undefined languages and applying the ADL setting
        for a in info.audio:
            try:
                if 'language' not in a.metadata or a.metadata['language'].strip() == "" or a.metadata['language'] is None:
                    a.metadata['language'] = 'und'
            except KeyError:
                a.metadata['language'] = 'und'

            # Set undefined language to default language if specified
            if self.settings.adl is not None and a.metadata['language'] == 'und':
                self.log.debug("Undefined language detected, defaulting to %s." % self.settings.adl)
                a.metadata['language'] = self.settings.adl

            if (awl and a.metadata['language'].lower() in awl):
                overrideLang = False

        if overrideLang and self.settings.allow_language_relax:
            awl = None
            self.log.info("No audio streams detected in any appropriate language, relaxing restrictions [allow-audio-language-relax].")

        # Prep subtitle streams by cleaning up languages and setting SDL
        for s in info.subtitle:
            try:
                if 'language' not in s.metadata or s.metadata['language'] == "" or s.metadata['language'] is None:
                    s.metadata['language'] = 'und'
            except KeyError:
                s.metadata['language'] = 'und'

            # Set undefined language to default language if specified
            if self.settings.sdl is not None and s.metadata['language'] == 'und':
                self.log.debug("Undefined language detected, defaulting to [%s]." % self.settings.sdl)
                s.metadata['language'] = self.settings.sdl
        return awl, swl

    # Generate a dict of options to be passed to FFMPEG based on selected settings and the source file parameters and streams
    def generateOptions(self, inputfile, info=None, original=None):
        # Get path information from the input file
        input_dir, filename, input_extension = self.parseFile(inputfile)
        sources = [inputfile]
        ripsubopts = []

        info = self.converter.probe(inputfile) if not info else info

        if not info:
            self.log.error("FFProbe returned no value for inputfile %s (exists: %s), either the file does not exist or is not a format FFPROBE can read." % (inputfile, os.path.exists(inputfile)))
            return None, None, None, None

        awl, swl = self.safeLanguage(info)

        try:
            self.log.info("Input Data")
            self.log.info(json.dumps(info.toJson, sort_keys=False, indent=4))
        except:
            self.log.exception("Unable to print input file data")

        # Video stream
        self.log.info("Reading video stream.")
        self.log.info("Video codec detected: %s." % info.video.codec)
        self.log.info("Pix Fmt: %s." % info.video.pix_fmt)
        self.log.info("Profile: %s." % info.video.profile)

        vdebug = "base"
        try:
            vbr = self.estimateVideoBitrate(info)
        except:
            if info.format.bitrate:
                vbr = info.format.bitrate / 1000

        if info.video.codec.lower() in self.settings.vcodec:
            vcodec = 'copy'
        else:
            vcodec = self.settings.vcodec[0]
        vbitrate = self.settings.vbitrate if self.settings.vbitrate else vbr

        try:
            vpix_fmt = self.settings.pix_fmt[0]
        except:
            vpix_fmt = None

        if self.settings.pix_fmt and info.video.pix_fmt.lower() not in self.settings.pix_fmt:
            self.log.debug("Overriding video pix_fmt. Codec cannot be copied because pix_fmt is not approved.")
            vdebug = vdebug + ".pix_fmt"
            vcodec = self.settings.vcodec[0]

        vbitrate = self.settings.vbitrate
        if self.settings.vbitrate is not None and vbr > self.settings.vbitrate:
            self.log.debug("Overriding video bitrate. Codec cannot be copied because video bitrate is too high [video-bitrate].")
            vdebug = vdebug + ".video-bitrate"
            vcodec = self.settings.vcodec[0]

        vwidth = self.settings.vwidth
        if self.settings.vwidth is not None and self.settings.vwidth < info.video.video_width:
            self.log.debug("Video width is over the max width, it will be downsampled. Video stream can no longer be copied [video-max-width].")
            vdebug = vdebug + ".video-max-width"
            vcodec = self.settings.vcodec[0]

        vlevel = self.settings.h264_level
        if '264' in info.video.codec.lower() and self.settings.h264_level and info.video.video_level and (info.video.video_level / 10 > self.settings.h264_level):
            self.log.debug("Video level %0.1f. Codec cannot be copied because video level is too high [h264-level]." % (info.video.video_level / 10))
            vdebug = vdebug + ".h264-max-level"
            vcodec = self.settings.vcodec[0]

        try:
            vprofile = self.settings.vprofile[0]
        except:
            vprofile = None

        if self.settings.vprofile and info.video.profile.lower().replace(" ", "") not in self.settings.vprofile:
            self.log.debug("Video profile is not supported. Video stream can no longer be copied [video-profile].")
            vdebug = vdebug + ".video-profile"
            vcodec = self.settings.vcodec[0]

        vfieldorder = info.video.field_order

        self.log.debug("Video codec: %s." % vcodec)
        self.log.debug("Video bitrate: %s." % vbitrate)
        self.log.debug("Video level: %s." % vlevel)
        self.log.debug("Video profile: %s." % vprofile)
        self.log.debug("Video pix format: %s." % vpix_fmt)
        self.log.debug("Video field order: %s." % vfieldorder)
        self.log.debug("Video width: %s." % vwidth)
        self.log.debug("Video debug %s." % vdebug)

        video_settings = {
            'codec': vcodec,
            'map': info.video.index,
            'bitrate': vbitrate,
            'level': vlevel,
            'profile': vprofile,
            'pix_fmt': vpix_fmt,
            'field_order': vfieldorder,
            'width': vwidth,
            'debug': vdebug,
        }

        # Audio streams
        self.log.info("Reading audio streams.")

        # Iterate through audio streams
        audio_settings = []
        blocked_audio_languages = []
        iOS = (self.settings.iOS is not False)

        # Sort incoming streams so that things like first language preferences respect these options
        audio_streams = info.audio
        try:
            self.sortStreams(audio_streams, awl)
        except:
            self.log.exception("Error sorting source audio streams [sort-streams].")

        for a in audio_streams:
            self.log.info("Audio detected for stream %s - %s %s %d channel." % (a.index, a.codec, a.metadata['language'], a.audio_channels))

            if self.settings.output_extension in valid_tagging_extensions and a.codec.lower() == 'truehd' and self.settings.ignore_truehd:
                if len(info.audio) > 1:
                    self.log.info("Skipping trueHD stream %s as typically the 2nd audio stream is the AC3 core of the truehd stream [ignore-truehd]." % a.index)
                    continue
                else:
                    self.log.info("TrueHD stream detected but no other audio streams in source, cannot skip stream %s [ignore-truehd]." % a.index)

            # Proceed if no whitelist is set, or if the language is in the whitelist
            iosdata = None
            if awl is None or (a.metadata['language'].lower() in awl and a.metadata['language'].lower() not in blocked_audio_languages):
                # Create iOS friendly audio stream if the default audio stream has too many channels (iOS only likes AAC stereo)
                if iOS and a.audio_channels > 2:
                    iOSbitrate = 256 if (self.settings.abitrate * 2) > 256 else (self.settings.abitrate * 2)

                    # Bitrate calculations/overrides
                    if self.settings.abitrate is 0:
                        self.log.debug("Attempting to set ios stream bitrate based on source stream bitrate.")
                        try:
                            iOSbitrate = ((a.bitrate / 1000) / a.audio_channels) * 2
                        except:
                            self.log.warning("Unable to determine iOS audio bitrate from source stream %s, defaulting to 128 per channel." % a.index)
                            iOSbitrate = 2 * 128

                    self.log.debug("Audio codec: %s." % self.settings.iOS[0])
                    self.log.debug("Channels: 2.")
                    self.log.debug("Filter: %s." % self.settings.iOSfilter)
                    self.log.debug("Bitrate: %s." % iOSbitrate)
                    self.log.debug("Language: %s." % a.metadata['language'])
                    self.log.debug("Disposition: %s." % a.disposition)

                    iosdata = {
                        'map': a.index,
                        'codec': self.settings.iOS[0],
                        'channels': 2,
                        'bitrate': iOSbitrate,
                        'filter': self.settings.iOSfilter,
                        'language': a.metadata['language'],
                        'disposition': a.disposition,
                        'debug': 'ios-audio'
                    }
                    if not self.settings.iOSLast:
                        self.log.info("Creating %s audio stream source audio stream %d [iOS-audio]." % (self.settings.iOS[0], a.index))
                        audio_settings.append(iosdata)

                adebug = "base"
                # If the iOS audio option is enabled and the source audio channel is only stereo, the additional iOS channel will be skipped and a single AAC 2.0 channel will be made regardless of codec preference to avoid multiple stereo channels
                if iOS and a.audio_channels <= 2:
                    self.log.debug("Overriding default channel settings because iOS audio is enabled but the source is stereo [iOS-audio].")
                    acodec = 'copy' if a.codec in self.settings.iOS else self.settings.iOS[0]
                    audio_channels = a.audio_channels
                    afilter = self.settings.iOSfilter
                    abitrate = a.audio_channels * 128 if (a.audio_channels * self.settings.abitrate) > (a.audio_channels * 128) else (a.audio_channels * self.settings.abitrate)
                    adebug = adebug + ".ios-audio"
                else:
                    # If desired codec is the same as the source codec, copy to avoid quality loss
                    acodec = 'copy' if a.codec.lower() in self.settings.acodec else self.settings.acodec[0]
                    afilter = self.settings.afilter
                    # Audio channel adjustments
                    if self.settings.maxchannels and a.audio_channels > self.settings.maxchannels:
                        self.log.debug("Audio source exceeds maximum channels, can not be copied. Settings channels to %d [audio-max-channels]." % self.settings.maxchannels)
                        adebug = adebug + ".audio-max-channels"
                        audio_channels = self.settings.maxchannels
                        acodec = self.settings.acodec[0]
                        abitrate = self.settings.maxchannels * self.settings.abitrate
                    else:
                        audio_channels = a.audio_channels
                        abitrate = a.audio_channels * self.settings.abitrate

                # Bitrate calculations/overrides
                if self.settings.abitrate is 0:
                    self.log.debug("Attempting to set bitrate based on source stream bitrate.")
                    try:
                        abitrate = ((a.bitrate / 1000) / a.audio_channels) * audio_channels
                    except:
                        self.log.warning("Unable to determine audio bitrate from source stream %s, defaulting to 256 per channel." % a.index)
                        abitrate = audio_channels * 256

                self.log.debug("Audio codec: %s." % acodec)
                self.log.debug("Channels: %s." % audio_channels)
                self.log.debug("Bitrate: %s." % abitrate)
                self.log.debug("Language: %s" % a.metadata['language'])
                self.log.debug("Filter: %s" % afilter)
                self.log.debug("Disposition: %s" % a.disposition)
                self.log.debug("Debug: %s" % adebug)

                # If the iOSFirst option is enabled, disable the iOS option after the first audio stream is processed
                if self.settings.iOS and self.settings.iOSFirst:
                    self.log.debug("Not creating any additional iOS audio streams [iOS-first-track-only].")
                    iOS = False

                absf = 'aac_adtstoasc' if acodec == 'copy' and a.codec == 'aac' and self.settings.aac_adtstoasc else None

                self.log.info("Creating %s audio stream from source stream %d." % (acodec, a.index))
                audio_settings.append({
                    'map': a.index,
                    'codec': acodec,
                    'channels': audio_channels,
                    'bitrate': abitrate,
                    'filter': afilter,
                    'language': a.metadata['language'],
                    'disposition': a.disposition,
                    'bsf': absf,
                    'debug': adebug
                })

                # Add the iOS stream last instead
                if self.settings.iOSLast and iosdata:
                    self.log.info("Creating %s audio stream from source audio stream %d [iOS-audio]." % (self.settings.iOS[0], a.index))
                    audio_settings.append(iosdata)

                if self.settings.audio_copyoriginal and acodec != 'copy' and not (a.codec.lower() == 'truehd' and self.settings.ignore_truehd):
                    self.log.info("Copying audio stream from source stream %d format %s [audio-copy-original]." % (a.index, a.codec))
                    audio_settings.append({
                        'map': a.index,
                        'codec': 'copy',
                        'channels': a.audio_channels,
                        'language': a.metadata['language'],
                        'disposition': a.disposition,
                        'debug': 'audio-copy-original'
                    })

                # Remove the language if we only want the first stream from a given language
                if self.settings.audio_first_language_track:
                    try:
                        blocked_audio_languages.append(a.metadata['language'].lower())
                        self.log.debug("Removing language from whitelist to prevent multiple streams of the same: %s [audio-first-track-of-language]." % a.metadata['language'])
                    except:
                        self.log.error("Unable to remove language %s from whitelist [audio-first-track-of-language]." % a.metadata['language'])

        # Set Default Audio Stream
        try:
            self.setDefaultAudioStream(audio_settings)
        except:
            self.log.exception("Unable to set the default audio track.")

        # Iterate through subtitle streams
        subtitle_settings = []
        self.log.info("Reading subtitle streams.")
        for s in info.subtitle:
            image_based = self.isImageBasedSubtitle(inputfile, s.index)
            self.log.info("%s-based subtitle detected for stream %s - %s %s." % ("Image" if image_based else "Text", s.index, s.codec, s.metadata['language']))

            scodec = None
            if image_based and self.settings.scodec_image and len(self.settings.scodec_image) > 0:
                scodec = 'copy' if s.codec in self.settings.scodec_image else self.settings.scodec_image[0]
            elif not image_based and self.settings.scodec and len(self.settings.scodec) > 0:
                scodec = 'copy' if s.codec in self.settings.scodec else self.settings.scodec[0]

            if self.settings.embedsubs and scodec:
                # Proceed if no whitelist is set, or if the language is in the whitelist
                if swl is None or s.metadata['language'].lower() in swl:
                    subtitle_settings.append({
                        'map': s.index,
                        'codec': scodec,
                        'language': s.metadata['language'],
                        'encoding': self.settings.subencoding,
                        'disposition': s.disposition,
                        'debug': 'base.embed-subs'
                    })
                    self.log.info("Creating %s subtitle stream from source stream %d." % (self.settings.scodec[0], s.index))
            elif not self.settings.embedsubs:
                if swl is None or s.metadata['language'].lower() in swl:
                    for codec in (self.settings.scodec_image if image_based else self.settings.scodec):
                        ripsub = [{
                            'map': s.index,
                            'codec': codec,
                            'language': s.metadata['language'],
                            'debug': "base"
                        }]
                        options = {
                            'source': [inputfile],
                            'format': codec,
                            'subtitle': ripsub,
                            'forced': s.forced,
                            'default': s.default,
                            'language': s.metadata['language'],
                            'index': s.index
                        }
                        ripsubopts.append(options)

        # Attempt to download subtitles if they are missing using subliminal
        try:
            self.downloadSubtitles(inputfile, info.subtitle, original)
        except:
            self.log.exception("Unable to download subitltes [download-subs].")

        # External subtitle import
        valid_external_subs = None
        if self.settings.embedsubs and not self.settings.embedonlyinternalsubs:  # Don't bother if we're not embeddeding subtitles and external subtitles
            valid_external_subs = self.scanForExternalSubs(inputfile, swl)
            for external_sub in valid_external_subs:
                image_based = self.isImageBasedSubtitle(external_sub.path, 0)
                scodec = None
                if image_based and self.settings.scodec_image and len(self.settings.scodec_image) > 0:
                    scodec = self.settings.scodec_image[0]
                elif not image_based and self.settings.scodec and len(self.settings.scodec) > 0:
                    scodec = self.settings.scodec[0]

                if not scodec:
                    self.log.info("Skipping external subtitle file %s, no appropriate codecs found." % os.path.basename(external_sub.path))
                    continue
                if external_sub.path not in sources:
                    sources.append(external_sub.path)
                subtitle_settings.append({
                    'source': sources.index(external_sub.path),
                    'map': 0,
                    'codec': scodec,
                    'disposition': external_sub.subtitle[0].disposition,
                    'language': external_sub.subtitle[0].metadata['language'],
                    'debug': 'base.embed-subs'})

                self.log.info("Creating %s subtitle stream by importing %s-based %s [embed-subs]." % (scodec, "Image" if image_based else "Text", os.path.basename(external_sub.path)))
                self.log.debug("Path: %s." % external_sub.path)
                self.log.debug("Codec: %s." % self.settings.scodec[0])
                self.log.debug("Langauge: %s." % external_sub.subtitle[0].metadata['language'])
                self.log.debug("Disposition: %s." % external_sub.subtitle[0].disposition)

                self.deletesubs.add(external_sub.path)

        # Set Default Subtitle Stream
        try:
            self.setDefaultSubtitleStream(subtitle_settings)
        except:
            self.log.exception("Unable to set the default subtitle track.")

        # Burn subtitles
        try:
            vfilter = self.burnSubtitleFilter(inputfile, info.subtitle, swl, valid_external_subs)
        except:
            vfilter = None
            self.log.exception("Encountered an error while trying to determine which subtitle stream for subtitle burn [burn-subtitle].")
        if vfilter:
            self.log.debug("Found valid subtitle stream to burn into video, video cannot be copied [burn-subtitles].")
            video_settings['codec'] = self.settings.vcodec[0]
            video_settings['filter'] = vfilter

        # Sort Options
        try:
            self.sortStreams(audio_settings, awl)
            self.sortStreams(subtitle_settings, swl)
        except:
            self.log.exception("Error sorting output stream options [sort-streams].")

        # Attachments
        attachments = []
        for f in info.attachment:
            if f.codec in self.settings.attachmentcodec:
                attachment = {
                    'map': f.index,
                    'codec': 'copy'
                }
                attachments.append(attachment)

        # Collect all options
        options = {
            'source': sources,
            'format': self.settings.output_format,
            'video': video_settings,
            'audio': audio_settings,
            'subtitle': subtitle_settings,
            'attachment': attachments
        }

        preopts = []
        postopts = ['-threads', self.settings.threads]

        if len(options['subtitle']) > 0:
            self.log.debug("Subtitle streams detected, adding fix_sub_duration option to preopts.")
            preopts.append('-fix_sub_duration')

        if vcodec != 'copy':
            try:
                preopts.extend(self.setAcceleration(info.video.codec))
            except:
                self.log.exception("Error when trying to determine hardware acceleration support.")

        if self.settings.preopts:
            preopts.extend(self.settings.preopts)

        if self.settings.postopts:
            postopts.extend(self.settings.postopts)

        # HEVC Tagging for copied streams
        if info.video.codec.lower() in ['x265', 'h265', 'hevc'] and vcodec == 'copy':
            postopts.extend(['-tag:v', 'hvc1'])
            self.log.info("Tagging copied video stream as hvc1")

        return options, preopts, postopts, ripsubopts

    def setAcceleration(self, video_codec):
        opts = []
        # Look up which codecs and which decoders/encoders are available in this build of ffmpeg
        codecs = self.converter.ffmpeg.codecs

        # Lookup which hardware acceleration platforms are available in this build of ffmpeg
        hwaccels = self.converter.ffmpeg.hwaccels

        # Find the first of the specified hardware acceleration platform that is available in this build of ffmpeg.  The order of specified hardware acceleration platforms determines priority.
        for hwaccel in self.settings.hwaccels:
            if hwaccel in hwaccels:
                self.log.info("%s hwaccel is supported by this ffmpeg build and will be used." % hwaccel)
                opts.extend(['-hwaccel', hwaccel])

                # If there's a decoder for this acceleration platform, also use it
                decoder = self.converter.ffmpeg.hwaccel_decoder(video_codec, hwaccel)
                if (decoder in codecs[video_codec]['decoders'] and decoder in self.settings.hwaccel_decoders):
                    self.log.info("%s decoder is also supported by this ffmpeg build and will also be used." % decoder)
                    opts.extend(['-vcodec', decoder])
                break
        return opts

    def setDefaultAudioStream(self, audio_settings):
        if len(audio_settings) > 0:
            audio_streams = sorted(audio_settings, key=lambda x: x['channels'], reverse=self.settings.prefer_more_channels)
            preferred_language_audio_streams = [x for x in audio_streams if x['language'] == self.settings.adl] if self.settings.adl else audio_streams
            default_stream = audio_streams[0]
            default_streams = [x for x in audio_streams if 'default' in x['disposition']]
            default_preferred_language_streams = [x for x in default_streams if x['language'] == self.settings.adl] if self.settings.adl else default_streams
            default_streams_not_in_preferred_language = [x for x in default_streams if x not in default_preferred_language_streams]

            self.log.debug("%d total audio streams with %d set to default disposition. %d defaults in your preferred language (%s), %d in other languages." % (len(audio_streams), len(default_streams), len(default_preferred_language_streams), self.settings.adl, len(default_streams_not_in_preferred_language)))
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
            self.log.info("Default audio stream set to %s %s %s channel stream [prefer-more-channels: %s]." % (default_stream['language'], default_stream['codec'], default_stream['channels'], self.settings.prefer_more_channels))
        else:
            self.log.debug("Audio output is empty, unable to set default audio streams.")

    def setDefaultSubtitleStream(self, subtitle_settings):
        if len(subtitle_settings) > 0 and self.settings.sdl:
            if len([x for x in subtitle_settings if 'default' in x['disposition']]) < 1:
                try:
                    default_stream = [x for x in subtitle_settings if x['language'] == self.settings.sdl][0]
                    default_stream['disposition'] = '+default'
                except:
                    subtitle_settings[0]['disposition'] = '+default'
            else:
                self.log.debug("Default subtitle stream already inherited from source material, will not override to subtitle-language-default.")
        else:
            self.log.debug("Subtitle output is empty or no default subtitle language is set, will not pass over subtitle output to set a default stream.")

    def sortStreams(self, streams, languages):
        if self.settings.sort_streams:
            self.log.debug("Reordering streams to be in accordance with approved languages and channels [sort-streams, prefer-more-channels].")
            if len(streams) > 0:
                if isinstance(streams[0], dict):
                    streams.sort(key=lambda x: x.get('channels', 999), reverse=self.settings.prefer_more_channels)
                    if languages:
                        streams.sort(key=lambda x: languages.index(x['language']) if x['language'] in languages else 999)
                else:
                    streams.sort(key=lambda x: x.audio_channels, reverse=self.settings.prefer_more_channels)
                    if languages:
                        streams.sort(key=lambda x: languages.index(x.metadata['language']) if x.metadata['language'] in languages else 999)

    def burnSubtitleFilter(self, inputfile, subtitle_streams, swl, valid_external_subs=None):
        if self.settings.burn_subtitles:
            if swl:
                subtitle_streams = sorted(subtitle_streams, key=lambda x: swl.index(x.metadata['language']) if x.metadata['language'] in swl else 999)
            sub_candidates = []
            if len(subtitle_streams) > 0:
                first_index = sorted([x.index for x in subtitle_streams])[0]

                # Filter subtitles to be burned based on setting
                if "forced" in self.settings.burn_subtitles and "default" in self.settings.burn_subtitles:
                    sub_candidates = [x for x in subtitle_streams if x.forced and x.default]
                elif "forced" in self.settings.burn_subtitles:
                    sub_candidates = [x for x in subtitle_streams if x.forced]
                elif "default" in self.settings.burn_subtitles:
                    sub_candidates = [x for x in subtitle_streams if x.default]
                elif "any" in self.settings.burn_subtitles:
                    sub_candidates = subtitle_streams

                # Filter out image based subtitles (until we can find a method to get this to work)
                sub_candidates = [x for x in sub_candidates if not self.isImageBasedSubtitle(inputfile, x.index)]

                if len(sub_candidates) > 0:
                    self.log.debug("Found %d potential sources from the included subs for burning [burn-subtitle]." % len(sub_candidates))
                    burn_sub = sub_candidates[0]
                    relative_index = burn_sub.index - first_index
                    self.log.info("Burning subtitle %d %s into video steram [burn-subtitles]." % (burn_sub.index, burn_sub.metadata['language']))
                    self.log.debug("Video codec cannot be copied because valid burn subtitle was found, setting to %s [burn-subtitle: %s]." % (self.settings.vcodec[0], self.settings.burn_subtitles))
                    return "subtitles='%s':si=%d" % (self.raw(os.path.abspath(inputfile)), relative_index)

            if self.settings.embedsubs:
                self.log.debug("No valid embedded subtitles for burning, search for external subtitles [embed-subs, burn-subtitle].")
                valid_external_subs = valid_external_subs if valid_external_subs else self.scanForExternalSubs(inputfile, swl)
                if "forced" in self.settings.burn_subtitles and "default" in self.settings.burn_subtitles:
                    sub_candidates = [x for x in valid_external_subs if x.subtitle[0].forced and x.subtitle[0].default]
                elif "forced" in self.settings.burn_subtitles:
                    sub_candidates = [x for x in valid_external_subs if x.subtitle[0].forced]
                elif "default" in self.settings.burn_subtitles:
                    sub_candidates = [x for x in valid_external_subs if x.subtitle[0].default]
                elif "any" in self.settings.burn_subtitles:
                    sub_candidates = valid_external_subs

                # Filter out image based subtitles (until we can find a method to get this to work)
                sub_candidates = [x for x in sub_candidates if not self.isImageBasedSubtitle(x.path, 0)]
                if len(sub_candidates) > 0:
                    burn_sub = sub_candidates[0]
                    self.log.info("Burning external subtitle %s %s into video steram [burn-subtitles, embed-subs]." % (os.path.basename(burn_sub.path), burn_sub.subtitle[0].metadata['language']))
                    return "subtitles='%s'" % (self.raw(os.path.abspath(burn_sub.path)))
            self.log.info("No valid subtitle stream candidates found to be burned into video stream [burn-subtitles].")
        return None

    def scanForExternalSubs(self, inputfile, swl):
        input_dir, filename, input_extension = self.parseFile(inputfile)
        valid_external_subs = []
        for dirName, subdirList, fileList in os.walk(input_dir):
            for fname in fileList:
                subname, subextension = os.path.splitext(fname)
                # Watch for appropriate file extension
                valid_external_sub = self.isValidSubtitleSource(os.path.join(dirName, fname))
                if valid_external_sub:
                    x, lang = os.path.splitext(subname)
                    while '.forced' in lang or '.default' in lang or lang.replace('.', "").isdigit():
                        x, lang = os.path.splitext(x)
                    lang = lang[1:]
                    # Using bablefish to convert a 2 language code to a 3 language code
                    if len(lang) is 2:
                        try:
                            babel = Language.fromalpha2(lang)
                            lang = babel.alpha3
                        except:
                            pass
                    valid_external_sub.subtitle[0].metadata['language'] = lang
                    # If subtitle file name and input video name are the same, proceed
                    if fname.startswith(filename):  # filename in fname:
                        self.log.debug("External %s subtitle file detected." % lang)
                        if swl is None or lang in swl:
                            disposition = ''
                            if ".default" in fname:
                                valid_external_sub.subtitle[0].default = True
                            if ".forced" in fname:
                                valid_external_sub.subtitle[0].forced = True
                            valid_external_subs.append(valid_external_sub)
                        else:
                            self.log.debug("Ignoring %s external subtitle stream due to language %s." % (fname, lang))
        self.log.info("Scanned for external subtitles and found %d results in your approved languages." % (len(valid_external_subs)))
        if swl:
            valid_external_subs.sort(key=lambda x: swl.index(x.subtitle[0].metadata['language']) if x.subtitle[0].metadata['language'] in swl else 999)

        return valid_external_subs

    def downloadSubtitles(self, inputfile, existing_subtitle_tracks, swl, original=None):
        if self.settings.downloadsubs:
            try:
                self.log.debug(subliminal.__version__)
            except:
                self.log.error("Subliminal is not installed, downloading subtitles aborted.")
                return None

            languages = set()
            if swl:
                for alpha3 in swl:
                    try:
                        languages.add(Language(alpha3))
                    except:
                        self.log.exception("Unable to add language for download with subliminal.")
            if self.settings.sdl:
                try:
                    languages.add(Language(self.settings.sdl))
                except:
                    self.log.exception("Unable to add language for download with subliminal.")

            if len(languages) < 1:
                self.log.error("No valid subtitle download languages detected, subtitles will not be downloaded.")
                return None

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

                subtitles = subliminal.download_best_subtitles([video], languages, hearing_impaired=self.settings.hearing_impaired, providers=self.settings.subproviders)
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
            os.chmod(path, self.settings.permissions.get('chmod', int('0755', 8)))
            if os.name != 'nt':
                os.chown(path, self.settings.permissions.get('uid', -1), self.settings.permissions.get('gid', -1))
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
        output_dir = input_dir if self.settings.output_dir is None else self.settings.output_dir
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
                conv = self.converter.convert(outputfile, options, timeout=None)
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
        output_dir = input_dir if self.settings.output_dir is None else self.settings.output_dir
        output_extension = temp_extension if temp_extension else self.settings.output_extension

        self.log.debug("Input directory: %s." % input_dir)
        self.log.debug("File name: %s." % filename)
        self.log.debug("Input extension: %s." % input_extension)
        self.log.debug("Output directory: %s." % output_dir)
        self.log.debug("Output extension: %s." % output_dir)

        counter = (".%d" % number) if number > 0 else ""

        try:
            outputfile = os.path.join(output_dir.decode(sys.getfilesystemencoding()), filename.decode(sys.getfilesystemencoding()) + counter + "." + output_extension).encode(sys.getfilesystemencoding())
        except:
            outputfile = os.path.join(output_dir, filename + counter + "." + output_extension)

        self.log.debug("Output file: %s." % outputfile)
        return outputfile, output_dir

    def isImageBasedSubtitle(self, inputfile, map):
        ripsub = [{'map': map, 'codec': 'srt'}]
        options = {'source': [inputfile], 'format': 'srt', 'subtitle': ripsub}
        try:
            conv = self.converter.convert(None, options, timeout=30)
            for timecode in conv:
                pass
        except FFMpegConvertError:
            return True
        except:
            self.log.exception("Unknown error when trying to determine if subtitle is image based.")
            return True
        return False

    def canBypassConvert(self, input_extension, options):
        # Process same extensions
        if self.settings.output_extension == input_extension:
            if not self.settings.forceConvert and not self.settings.process_same_extensions:
                self.log.info("Input and output extensions are the same so passing back the original file [process-same-extensions: %s]." % self.settings.process_same_extensions)
                return True
            # Force convert
            elif not self.settings.forceConvert and len([x for x in [options['video']] + [x for x in options['audio']] + [x for x in options['subtitle']] if x['codec'] != 'copy']) == 0:
                self.log.info("Input and output extensions match and every codec is copy, this file probably doesn't need conversion, returning [force-convert: %s]." % self.settings.forceConvert)
                return True
            elif self.settings.forceConvert:
                self.log.info("Input and output extensions match and every codec is copy, this file probably doesn't need conversion, but conversion being forced [force-convert: %s]." % self.settings.forceConvert)
        return False

    # Encode a new file based on selected options, built in naming conflict resolution
    def convert(self, options, preopts, postopts, reportProgress=False):
        self.log.info("Starting conversion.")
        inputfile = options['source'][0]
        input_dir, filename, input_extension = self.parseFile(inputfile)
        originalinputfile = inputfile
        outputfile, output_dir = self.getOutputFile(input_dir, filename, input_extension, self.settings.temp_extension)
        finaloutputfile, _ = self.getOutputFile(input_dir, filename, input_extension)

        self.log.debug("Final output file: %s." % finaloutputfile)

        if len(options['audio']) == 0:
            self.log.error("Conversion has no audio streams, aborting")
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
                    og = "%s.%d.original" % (inputfile, i)
                    i += 1
                os.rename(inputfile, og)
                if self.settings.burn_subtitles:
                    try:
                        if self.raw(os.path.abspath(inputfile)) in options['video'].get('filter', ""):
                            self.log.debug("Renaming inputfile in burnsubtitles filter if its present [burn-subtitles].")
                            options['video']['filter'] = options['video']['filter'].replace(self.raw(os.path.abspath(inputfile)), self.raw(os.path.abspath(og)))
                    except:
                        self.log.exception("Error trying to rename filter [burn-subtitles].")
                inputfile = og
                options['source'][0] = og
                self.log.debug("Renamed original file to %s." % inputfile)

            except:
                i = 2
                while os.path.isfile(finaloutputfile):
                    outputfile, output_dir = self.getOutputFile(input_dir, filename, input_extension, self.settings.temp_extension, number=i)
                    finaloutputfile, _ = self.getOutputFile(input_dir, filename, input_extension, number=i)
                    i += 1
                self.log.debug("Unable to rename inputfile. Alternatively renaming output file to %s." % outputfile)

        # Delete output file if it already exists and deleting enabled
        if os.path.exists(outputfile) and self.settings.delete:
            self.removeFile(outputfile)

        # Final sweep to make sure outputfile does not exist, renaming as the final solution
        i = 2
        while os.path.isfile(outputfile):
            outputfile, output_dir = self.getOutputFile(input_dir, filename, input_extension, self.settings.temp_extension, number=i)
            finaloutputfile, _ = self.getOutputFile(input_dir, filename, input_extension, number=i)
            i += 1

        try:
            conv = self.converter.convert(outputfile, options, timeout=None, preopts=preopts, postopts=postopts)
        except:
            self.log.exception("Error converting file.")
            return None, inputfile

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
        if os.path.isfile(inputfile) and self.settings.relocate_moov:
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

        if self.settings.copyto:
            self.log.debug("Copyto option is enabled.")
            for d in self.settings.copyto:
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

        if self.settings.moveto:
            self.log.debug("Moveto option is enabled.")
            moveto = os.path.join(self.settings.moveto, relativePath) if relativePath else self.settings.moveto
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

    def raw(self, text):
        escape_dict = {'\\': r'\\',
                       ':': "\\:"}
        output = ''
        for char in text:
            try:
                output += escape_dict[char]
            except KeyError:
                output += char
        return output
