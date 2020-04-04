from __future__ import unicode_literals
import os
import time
import json
import sys
import shutil
import logging
import re
from converter import Converter, FFMpegConvertError, ConverterError
from converter.avcodecs import BaseCodec
from resources.extensions import subtitle_codec_extensions
from resources.metadata import Metadata
from resources.postprocess import PostProcessor
from resources.lang import getAlpha3TCode
from autoprocess import plex
try:
    from babelfish import Language
except:
    pass
try:
    import subliminal
except:
    pass


class MediaProcessor:
    deletesubs = set()
    default_channel_bitrate = 128

    def __init__(self, settings, logger=None):
        self.log = logger or logging.getLogger(__name__)
        self.settings = settings
        self.converter = Converter(settings.ffmpeg, settings.ffprobe)

    def fullprocess(self, inputfile, mediatype, reportProgress=False, original=None, info=None, tmbdid=None, tvdbid=None, imdbid=None, season=None, episode=None, language=None):
        try:
            if not language:
                language = self.settings.taglanguage

            info = self.isValidSource(inputfile)
            if info:
                self.log.info("Processing %s." % inputfile)

                output = self.process(inputfile, original=original, info=info)

                if output:
                    # Tag with metadata
                    try:
                        tag = Metadata(mediatype, tvdbid=tvdbid, tmdbid=tmbdid, imdbid=imdbid, season=season, episode=episode, original=original, language=language)
                        if self.settings.tagfile:
                            self.log.info("Tagging %s with TMDB ID %s." % (inputfile, tag.tmdbid))
                            tag.writeTags(output['output'], self.settings.artwork, self.settings.thumbnail, output['x'], output['y'])
                    except:
                        self.log.exception("Unable to tag file")

                    # QTFS
                    if self.settings.relocate_moov:
                        self.QTFS(output['output'])

                    # Copy to additional locations
                    output_files = self.replicate(output['output'])

                    # Run any post process scripts
                    if self.settings.postprocess:
                        postprocessor = PostProcessor(output_files, self.log)
                        postprocessor.setEnv(mediatype, tag.tmdbid, season, episode)
                        postprocessor.run_scripts()

                    # Refresh Plex
                    if self.settings.Plex.get('refresh', False):
                        try:
                            plex.refreshPlex(self.settings, mediatype, self.log)
                        except:
                            self.log.exception("Error refreshing Plex.")
                    return True
            else:
                self.log.info("File %s is not valid" % inputfile)
        except:
            self.log.exception("Error processing")
        return False

    # Process a file from start to finish, with checking to make sure formats are compatible with selected settings
    def process(self, inputfile, reportProgress=False, original=None, info=None):
        self.log.debug("Process started.")

        delete = self.settings.delete
        deleted = False
        options = None
        preopts = None
        postopts = None
        outputfile = None
        ripped_subs = []
        downloaded_subs = []

        info = info or self.isValidSource(inputfile)

        if info:
            if self.canBypassConvert(inputfile, info):
                outputfile = inputfile
                self.log.info("Bypassing conversion and setting outputfile to inputfile.")
            else:
                try:
                    options, preopts, postopts, ripsubopts, downloaded_subs = self.generateOptions(inputfile, info=info, original=original)
                except:
                    self.log.exception("Unable to generate options, unexpected exception occurred.")
                    return None

                if not options:
                    self.log.error("Error converting, inputfile %s had a valid extension but returned no data. Either the file does not exist, was unreadable, or was an incorrect format." % inputfile)
                    return None

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
                    if self.settings.downloadsubs:
                        self.log.info("Downloaded Subtitles")
                        self.log.info(json.dumps(downloaded_subs, sort_keys=False, indent=4))

                except:
                    self.log.exception("Unable to log options.")

                ripped_subs = self.ripSubs(inputfile, ripsubopts)
                try:
                    outputfile, inputfile = self.convert(options, preopts, postopts, reportProgress)
                except:
                    self.log.exception("Unexpected exception encountered during conversion")
                    return None

            if not outputfile:
                self.log.debug("Error converting, no outputfile generated for inputfile %s." % inputfile)
                return None

            self.log.debug("%s created from %s successfully." % (outputfile, inputfile))

            if outputfile == inputfile:
                self.settings.deletesubs = set()
                if self.settings.output_dir:
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
            input_extension = self.parseFile(inputfile)[2]
            output_extension = self.parseFile(outputfile)[2]

            return {'input': inputfile,
                    'input_extension': input_extension,
                    'input_deleted': deleted,
                    'output': outputfile,
                    'output_extension': output_extension,
                    'options': options,
                    'preopts': preopts,
                    'postopts': postopts,
                    'external_subs': downloaded_subs + ripped_subs,
                    'x': dim['x'],
                    'y': dim['y']}
        return None

    def cleanDispositions(self, info):
        for stream in info.streams:
            for dispo in self.settings.sanitizedisposition:
                self.log.debug("Setting %s to False for stream %d [santizie-disposition]." % (dispo, stream.index))
                stream.disposition[dispo] = False

    def audioStreamTitle(self, channels, disposition):
        output = "Audio"
        if channels == 1:
            output = "Mono"
        elif channels == 2:
            output = "Stereo"
        elif channels > 2:
            output = "%d.1 Channel" % (channels - 1)

        if disposition.get("comment"):
            output += " (Commentary)"
        if disposition.get("hearing_impaired"):
            output += " (Hearing Impaired)"
        if disposition.get("visual_impaired"):
            output += " (Visual Impaired)"
        if disposition.get("dub"):
            output += " (Dub)"

        return output

    def subtitleStreamTitle(self, disposition):
        output = ""
        if disposition.get("forced"):
            output += "Forced "
        if disposition.get("hearing_impaired"):
            output += "Hearing Impaired "
        if disposition.get("comment"):
            output += "Commentary "
        if disposition.get("visual_impaired"):
            output += "Visual Impaired "
        if disposition.get("dub"):
            output += "Dub "
        return output.strip()

    # Determine if a file can be read by FFPROBE
    def isValidSource(self, inputfile):
        try:
            extension = self.parseFile(inputfile)[2]
            if extension in self.settings.ignored_extensions:
                return None
            if self.settings.minimum_size > 0 and os.path.getsize(inputfile) < (self.settings.minimum_size * 1000000):
                self.log.debug("Invalid source, below minimum size threshold [minimum-size].")
                return None
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
        try:
            total_bitrate = info.format.bitrate
            audio_bitrate = 0
            for a in info.audio:
                audio_bitrate += a.bitrate

            self.log.debug("Total bitrate is %s." % info.format.bitrate)
            self.log.debug("Total audio bitrate is %s." % audio_bitrate)
            self.log.debug("Estimated video bitrate is %s." % (total_bitrate - audio_bitrate))
            return ((total_bitrate - audio_bitrate) / 1000) * .95
        except:
            if info.format.bitrate:
                return info.format.bitrate / 1000
        return 0

    # Generate a JSON formatter dataset with the input and output information and ffmpeg command for a theoretical conversion
    def jsonDump(self, inputfile, original=None):
        dump = {}
        dump["input"], info = self.generateSourceDict(inputfile)
        if self.canBypassConvert(inputfile, info):
            dump["output"] = dump["input"]
            dump["output"]["bypassConvert"] = True
        else:
            dump["output"], dump["preopts"], dump["postopts"], dump["ripsubopts"], dump["downloadedsubs"] = self.generateOptions(inputfile, original)
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
            for sub in dump["downloadedsubs"]:
                self.log.debug("Cleaning up downloaded sub %s which was only used to simulate options." % (sub))
                self.removeFile(sub)

        return json.dumps(dump, sort_keys=False, indent=4)

    # Generate a dict of data about a source file
    def generateSourceDict(self, inputfile):
        output = {}
        input_dir, filename, input_extension = self.parseFile(inputfile)
        output['extension'] = input_extension
        probe = self.converter.probe(inputfile)
        self.titleDispositionCheck(probe)
        if probe:
            output.update(probe.json)
        else:
            output['error'] = "Invalid input, unable to read"
        return output, probe

    # Pass over audio and subtitle streams to ensure the language properties are safe, return any adjustments made to SWL/AWL if relax is enabled
    def safeLanguage(self, info):
        awl = self.settings.awl
        swl = self.settings.swl
        overrideLang = (len(awl) > 0)

        # Loop through audio streams and clean up language metadata by standardizing undefined languages and applying the ADL setting
        for a in info.audio:
            a.metadata['language'] = getAlpha3TCode(a.metadata.get('language'), self.settings.adl)
            if len(awl) > 0 and a.metadata.get('language') in awl:
                overrideLang = False

        if overrideLang and self.settings.allow_language_relax:
            awl = []
            self.log.info("No audio streams detected in any appropriate language, relaxing restrictions [allow-audio-language-relax].")

        # Prep subtitle streams by cleaning up languages and setting SDL
        for s in info.subtitle:
            s.metadata['language'] = getAlpha3TCode(s.metadata.get('language'), self.settings.sdl)
        return awl, swl

    # Check and see if clues about the disposition are in the title
    def titleDispositionCheck(self, info):
        for stream in info.streams:
            title = stream.metadata.get('title', '')
            if 'comment' in title:
                self.log.debug("Found comment in stream title, setting comment disposition to True.")
                stream.disposition['comment'] = True
            if 'hearing' in title:
                self.log.debug("Found hearing in stream title, setting hearing_impaired disposition to True.")
                stream.disposition['hearing_impaired'] = True
            if 'visual' in title:
                self.log.debug("Found visual in stream title, setting visual_impaired disposition to True.")
                stream.disposition['visual_impaired'] = True
            if 'forced' in title:
                self.log.debug("Found foced in stream title, setting forced disposition to True.")
                stream.disposition['forced'] = True


    # Generate a dict of options to be passed to FFMPEG based on selected settings and the source file parameters and streams
    def generateOptions(self, inputfile, info=None, original=None):
        # Get path information from the input file
        sources = [inputfile]
        ripsubopts = []

        info = info or self.converter.probe(inputfile)

        if not info:
            self.log.error("FFPROBE returned no value for inputfile %s (exists: %s), either the file does not exist or is not a format FFPROBE can read." % (inputfile, os.path.exists(inputfile)))
            return None, None, None, None

        awl, swl = self.safeLanguage(info)
        self.titleDispositionCheck(info)
        self.cleanDispositions(info)

        try:
            self.log.info("Input Data")
            self.log.info(json.dumps(info.json, sort_keys=False, indent=4))
        except:
            self.log.exception("Unable to print input file data")

        # Video stream
        self.log.info("Reading video stream.")
        self.log.info("Video codec detected: %s." % info.video.codec)
        self.log.info("Pix Fmt: %s." % info.video.pix_fmt)
        self.log.info("Profile: %s." % info.video.profile)

        vdebug = "video"
        vcodec = "copy" if info.video.codec in self.settings.vcodec else self.settings.vcodec[0]

        vpix_fmt = None
        if len(self.settings.pix_fmt) > 0 and info.video.pix_fmt not in self.settings.pix_fmt:
            self.log.debug("Overriding video pix_fmt. Codec cannot be copied because pix_fmt is not approved [pix-fmt].")
            vdebug = vdebug + ".pix_fmt"
            vcodec = self.settings.vcodec[0]
            vpix_fmt = self.settings.pix_fmt[0]

        vbitrate_estimate = self.estimateVideoBitrate(info)
        vbitrate = vbitrate_estimate
        if self.settings.vmaxbitrate and vbitrate > self.settings.vmaxbitrate:
            self.log.debug("Overriding video bitrate. Codec cannot be copied because video bitrate is too high [video-max-bitrate].")
            vdebug = vdebug + ".max-bitrate"
            vcodec = self.settings.vcodec[0]
            vbitrate = self.settings.vmaxbitrate

        vwidth = None
        if self.settings.vwidth and self.settings.vwidth < info.video.video_width:
            self.log.debug("Video width is over the max width, it will be downsampled. Video stream can no longer be copied [video-max-width].")
            vdebug = vdebug + ".max-width"
            vcodec = self.settings.vcodec[0]
            vwidth = self.settings.vwidth

        vlevel = self.settings.video_level
        if self.settings.video_level and info.video.video_level and (info.video.video_level / 10 > self.settings.video_level):
            self.log.debug("Video level %0.1f. Codec cannot be copied because video level is too high [video-max-level]." % (info.video.video_level / 10))
            vdebug = vdebug + ".max-level"
            vcodec = self.settings.vcodec[0]

        vprofile = None
        if len(self.settings.vprofile) > 0 and info.video.profile not in self.settings.vprofile:
            self.log.debug("Video profile is not supported. Video stream can no longer be copied [video-profile].")
            vdebug = vdebug + ".profile"
            vcodec = self.settings.vcodec[0]
            vprofile = self.settings.vprofile[0]

        vfieldorder = info.video.field_order

        vcrf = self.settings.vcrf
        vmaxrate = None
        vbufsize = None
        if len(self.settings.vcrf_profiles) > 0:
            self.log.debug("VCRF profiles detected [video-crf-profiles].")
            for profile in self.settings.vcrf_profiles:
                try:
                    if profile['source_bitrate'] < vbitrate_estimate:
                        vcrf = profile['crf']
                        vmaxrate = profile['maxrate']
                        vbufsize = profile['bufsize']
                        self.log.info("Acceptable profile match found for VBR %s using CRF %d, maxrate %s, bufsize %s." % (vbitrate_estimate, vcrf, vmaxrate, vbufsize))
                        break
                except:
                    self.log.exception("Error setting VCRF profile information.")

        self.log.debug("Video codec: %s." % vcodec)
        self.log.debug("Video bitrate: %s." % vbitrate)
        self.log.debug("Video CRF: %s." % vcrf)
        self.log.debug("Video maxrate: %s." % vmaxrate)
        self.log.debug("Video bufsize: %s." % vbufsize)
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
            'crf': vcrf,
            'maxrate': vmaxrate,
            'bufsize': vbufsize,
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
        ua = (len(self.settings.ua) > 0)

        # Sort incoming streams so that things like first language preferences respect these options
        audio_streams = info.audio
        try:
            self.sortStreams(audio_streams, awl)
        except:
            self.log.exception("Error sorting source audio streams [sort-streams].")

        for a in audio_streams:
            self.log.info("Audio detected for stream %s - %s %s %d channel." % (a.index, a.codec, a.metadata['language'], a.audio_channels))

            if a.codec == 'truehd' and self.settings.output_extension in self.settings.ignore_truehd:
                if len(info.audio) > 1:
                    self.log.info("Skipping trueHD stream %s as typically the 2nd audio stream is the AC3 core of the truehd stream [audio-ignore-truehd]." % a.index)
                    continue
                else:
                    self.log.info("TrueHD stream detected but no other audio streams in source, cannot skip stream %s [audio-ignore-truehd]." % a.index)

            # Proceed if no whitelist is set, or if the language is in the whitelist
            uadata = None
            if self.validLanguage(a.metadata['language'], awl, blocked_audio_languages):
                # Create friendly audio stream if the default audio stream has too many channels
                if ua and a.audio_channels > 2:
                    if self.settings.ua_bitrate == 0:
                        self.log.warning("Universal audio channel bitrate must be greater than 0, defaulting to %d [universal-audio-channel-bitrate]." % self.default_channel_bitrate)
                        self.settings.ua_bitrate = self.default_channel_bitrate
                    ua_bitrate = (self.default_channel_bitrate * 2) if (self.settings.ua_bitrate * 2) > (self.default_channel_bitrate * 2) else (self.settings.ua_bitrate * 2)
                    ua_disposition = a.dispostr

                    # Bitrate calculations/overrides
                    if self.settings.ua_bitrate == 0:
                        self.log.debug("Attempting to set universal audio stream bitrate based on source stream bitrate.")
                        try:
                            ua_bitrate = ((a.bitrate / 1000) / a.audio_channels) * 2
                        except:
                            self.log.warning("Unable to determine universal audio bitrate from source stream %s, defaulting to %d per channel." % (a.index, self.default_channel_bitrate))
                            ua_bitrate = 2 * self.default_channel_bitrate

                    self.log.debug("Audio codec: %s." % self.settings.ua[0])
                    self.log.debug("Channels: 2.")
                    self.log.debug("Filter: %s." % self.settings.ua_filter)
                    self.log.debug("Bitrate: %s." % ua_bitrate)
                    self.log.debug("Language: %s." % a.metadata['language'])
                    self.log.debug("Disposition: %s." % ua_disposition)

                    uadata = {
                        'map': a.index,
                        'codec': self.settings.ua[0],
                        'channels': 2,
                        'bitrate': ua_bitrate,
                        'samplerate': self.settings.audio_samplerates[0] if len(self.settings.audio_samplerates) > 0 else None,
                        'filter': self.settings.ua_filter,
                        'language': a.metadata['language'],
                        'disposition': ua_disposition,
                        'title': self.audioStreamTitle(2, a.disposition),
                        'debug': 'universal-audio'
                    }
                    if not self.settings.ua_last:
                        self.log.info("Creating %s audio stream source audio stream %d [universal-audio]." % (self.settings.ua[0], a.index))
                        audio_settings.append(uadata)

                adebug = "audio"
                # If the universal audio option is enabled and the source audio channel is only stereo, the additional universal stream will be skipped and a single channel will be made regardless of codec preference to avoid multiple stereo channels
                afilter = None
                asample = None
                adisposition = a.dispostr
                if ua and a.audio_channels <= 2:
                    self.log.debug("Overriding default channel settings because universal audio is enabled but the source is stereo [universal-audio].")
                    acodec = 'copy' if a.codec in self.settings.ua else self.settings.ua[0]
                    audio_channels = a.audio_channels
                    abitrate = (a.audio_channels * self.default_channel_bitrate) if (a.audio_channels * self.settings.ua_bitrate) > (a.audio_channels * self.default_channel_bitrate) else (a.audio_channels * self.settings.ua_bitrate)
                    adebug = "universal-audio"

                    # UA Filters
                    if self.settings.ua_filter:
                        self.log.debug("Unable to copy codec because an universal audio filter is set [universal-audio-filter].")
                        afilter = self.settings.ua_filter
                        acodec = self.settings.ua[0]
                        adebug = adebug + ".filter"

                    # Sample rates
                    if len(self.settings.audio_samplerates) > 0 and a.audio_samplerate not in self.settings.audio_samplerates:
                        self.log.debug("Unable to copy codec because audio sample rate %d is not approved [audio-sample-rates]." % (a.audio_samplerate))
                        asample = self.settings.audio_samplerates[0]
                        acodec = self.settings.ua[0]
                        adebug = adebug + ".audio-sample-rates"
                else:
                    # If desired codec is the same as the source codec, copy to avoid quality loss
                    acodec = 'copy' if a.codec in self.settings.acodec else self.settings.acodec[0]
                    # Audio channel adjustments
                    if self.settings.maxchannels and a.audio_channels > self.settings.maxchannels:
                        self.log.debug("Audio source exceeds maximum channels, can not be copied. Settings channels to %d [audio-max-channels]." % self.settings.maxchannels)
                        adebug = adebug + ".max-channels"
                        audio_channels = self.settings.maxchannels
                        acodec = self.settings.acodec[0]
                        abitrate = self.settings.maxchannels * self.settings.abitrate
                    else:
                        audio_channels = a.audio_channels
                        abitrate = a.audio_channels * self.settings.abitrate

                    # Filters
                    if self.settings.afilter:
                        self.log.debug("Unable to copy codec because an audio filter is set [audio-filter].")
                        afilter = self.settings.afilter
                        acodec = self.settings.acodec[0]
                        adebug = adebug + ".audio-filter"

                    # Sample rates
                    if len(self.settings.audio_samplerates) > 0 and a.audio_samplerate not in self.settings.audio_samplerates:
                        self.log.info("Unable to copy codec because audio sample rate %d is not approved [audio-sample-rates]." % (a.audio_samplerate))
                        asample = self.settings.audio_samplerates[0]
                        acodec = self.settings.acodec[0]
                        adebug = adebug + ".audio-sample-rates"

                # Bitrate calculations/overrides
                if self.settings.abitrate == 0:
                    self.log.debug("Attempting to set bitrate based on source stream bitrate.")
                    try:
                        abitrate = ((a.bitrate / 1000) / a.audio_channels) * audio_channels
                    except:
                        self.log.warning("Unable to determine audio bitrate from source stream %s, defaulting to %d per channel." % (a.index, self.default_channel_bitrate))
                        abitrate = audio_channels * self.default_channel_bitrate
                if self.settings.amaxbitrate and abitrate > self.settings.amaxbitrate:
                    self.log.debug("Calculated bitrate of %d exceeds maximum bitrate %d, setting to max value [audio-max-bitrate]." % (abitrate, self.settings.amaxbitrate))
                    abitrate = self.settings.amaxbitrate

                self.log.debug("Audio codec: %s." % acodec)
                self.log.debug("Channels: %s." % audio_channels)
                self.log.debug("Bitrate: %s." % abitrate)
                self.log.debug("Language: %s" % a.metadata['language'])
                self.log.debug("Filter: %s" % afilter)
                self.log.debug("Disposition: %s" % adisposition)
                self.log.debug("Debug: %s" % adebug)

                # If the ua_first_only option is enabled, disable the ua option after the first audio stream is processed
                if ua and self.settings.ua_first_only:
                    self.log.debug("Not creating any additional universal audio streams [universal-audio-first-stream-only].")
                    ua = False

                absf = 'aac_adtstoasc' if acodec == 'copy' and a.codec == 'aac' and self.settings.aac_adtstoasc else None

                self.log.info("Creating %s audio stream from source stream %d." % (acodec, a.index))
                audio_settings.append({
                    'map': a.index,
                    'codec': acodec,
                    'channels': audio_channels,
                    'bitrate': abitrate,
                    'filter': afilter,
                    'samplerate': asample,
                    'language': a.metadata['language'],
                    'disposition': adisposition,
                    'bsf': absf,
                    'title': self.audioStreamTitle(audio_channels, a.disposition),
                    'debug': adebug
                })

                # Add the universal audio stream last instead
                if self.settings.ua_last and uadata:
                    self.log.info("Creating %s audio stream from source audio stream %d [universal-audio]." % (self.settings.ua[0], a.index))
                    audio_settings.append(uadata)

                if self.settings.audio_copyoriginal and acodec != 'copy' and not (a.codec == 'truehd' and self.settings.output_extension in self.settings.ignore_truehd):
                    self.log.info("Copying audio stream from source stream %d format %s [audio-copy-original]." % (a.index, a.codec))
                    audio_settings.append({
                        'map': a.index,
                        'codec': 'copy',
                        'channels': a.audio_channels,
                        'language': a.metadata['language'],
                        'disposition': adisposition,
                        'title': self.audioStreamTitle(a.audio_channels, a.disposition),
                        'debug': 'audio-copy-original'
                    })

                # Remove the language if we only want the first stream from a given language
                if self.settings.audio_first_language_stream:
                    blocked_audio_languages.append(a.metadata['language'])
                    self.log.debug("Blocking further %s audio streams to prevent multiple streams of the same language [audio-first-stream-of-language]." % a.metadata['language'])

        # Set Default Audio Stream
        try:
            self.setDefaultAudioStream(audio_settings)
        except:
            self.log.exception("Unable to set the default audio stream.")

        # Iterate through subtitle streams
        subtitle_settings = []
        blocked_subtitle_languages = []
        self.log.info("Reading subtitle streams.")
        if not self.settings.ignore_embedded_subs:
            for s in info.subtitle:
                try:
                    image_based = self.isImageBasedSubtitle(inputfile, s.index)
                except:
                    self.log.error("Unknown error occurred while trying to determine if subtitle is text or image based. Probably corrupt, skipping.")
                    continue
                self.log.info("%s-based subtitle detected for stream %s - %s %s." % ("Image" if image_based else "Text", s.index, s.codec, s.metadata['language']))

                scodec = None
                sdisposition = s.dispostr
                if image_based and self.settings.embedimgsubs and self.settings.scodec_image and len(self.settings.scodec_image) > 0:
                    scodec = 'copy' if s.codec in self.settings.scodec_image else self.settings.scodec_image[0]
                elif not image_based and self.settings.embedsubs and self.settings.scodec and len(self.settings.scodec) > 0:
                    scodec = 'copy' if s.codec in self.settings.scodec else self.settings.scodec[0]

                if scodec:
                    # Proceed if no whitelist is set, or if the language is in the whitelist
                    if self.validLanguage(s.metadata['language'], swl, blocked_subtitle_languages):
                        subtitle_settings.append({
                            'map': s.index,
                            'codec': scodec,
                            'language': s.metadata['language'],
                            'encoding': self.settings.subencoding,
                            'disposition': sdisposition,
                            'title': self.subtitleStreamTitle(s.disposition),
                            'debug': 'subtitle.embed-subs'
                        })
                        self.log.info("Creating %s subtitle stream from source stream %d." % (self.settings.scodec[0], s.index))
                        if self.settings.sub_first_language_stream:
                            blocked_subtitle_languages.append(s.metadata['language'])
                else:
                    if self.validLanguage(s.metadata['language'], swl, blocked_subtitle_languages):
                        for codec in (self.settings.scodec_image if image_based else self.settings.scodec):
                            ripsub = [{
                                'map': s.index,
                                'codec': codec,
                                'language': s.metadata['language'],
                                'debug': "subtitle"
                            }]
                            options = {
                                'source': [inputfile],
                                'format': codec,
                                'subtitle': ripsub,
                                'disposition': s.dispostr,
                                'language': s.metadata['language'],
                                'index': s.index
                            }
                            ripsubopts.append(options)
                        if self.settings.sub_first_language_stream:
                            blocked_subtitle_languages.append(s.metadata['language'])

        # Attempt to download subtitles if they are missing using subliminal
        downloaded_subs = []
        try:
            downloaded_subs = self.downloadSubtitles(inputfile, info.subtitle, swl, original)
        except:
            self.log.exception("Unable to download subitltes [download-subs].")

        # External subtitle import
        valid_external_subs = None
        if not self.settings.embedonlyinternalsubs:
            valid_external_subs = self.scanForExternalSubs(inputfile, swl)
            for external_sub in valid_external_subs:
                try:
                    image_based = self.isImageBasedSubtitle(external_sub.path, 0)
                except:
                    self.log.error("Unknown error occurred while trying to determine if subtitle is text or image based. Probably corrupt, skipping.")
                    continue
                scodec = None
                self.cleanDispositions(external_sub)
                sdisposition = external_sub.subtitle[0].dispostr
                if image_based and self.settings.embedimgsubs and self.settings.scodec_image and len(self.settings.scodec_image) > 0:
                    scodec = self.settings.scodec_image[0]
                elif not image_based and self.settings.embedsubs and self.settings.scodec and len(self.settings.scodec) > 0:
                    scodec = self.settings.scodec[0]

                if not scodec:
                    self.log.info("Skipping external subtitle file %s, no appropriate codecs found or embed disabled." % os.path.basename(external_sub.path))
                    continue

                if self.validLanguage(external_sub.subtitle[0].metadata['language'], swl, blocked_subtitle_languages):
                    if external_sub.path not in sources:
                        sources.append(external_sub.path)
                    subtitle_settings.append({
                        'source': sources.index(external_sub.path),
                        'map': 0,
                        'codec': scodec,
                        'disposition': sdisposition,
                        'title': self.subtitleStreamTitle(external_sub.subtitle[0].disposition),
                        'language': external_sub.subtitle[0].metadata['language'],
                        'debug': 'subtitle.embed-subs'})

                    self.log.info("Creating %s subtitle stream by importing %s-based %s [embed-subs]." % (scodec, "Image" if image_based else "Text", os.path.basename(external_sub.path)))
                    self.log.debug("Path: %s." % external_sub.path)
                    self.log.debug("Codec: %s." % self.settings.scodec[0])
                    self.log.debug("Langauge: %s." % external_sub.subtitle[0].metadata['language'])
                    self.log.debug("Disposition: %s." % sdisposition)

                    self.deletesubs.add(external_sub.path)

                    if self.settings.sub_first_language_stream:
                        blocked_subtitle_languages.append(external_sub.subtitle[0].metadata['language'])

        # Set Default Subtitle Stream
        try:
            self.setDefaultSubtitleStream(subtitle_settings)
        except:
            self.log.exception("Unable to set the default subtitle stream.")

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
        postopts = ['-threads', str(self.settings.threads), '-metadata:g', 'encoding_tool=SMA']

        if len(options['subtitle']) > 0:
            self.log.debug("Subtitle streams detected, adding fix_sub_duration option to preopts.")
            preopts.append('-fix_sub_duration')

        if vcodec != 'copy':
            try:
                preopts.extend(self.setAcceleration(info.video.codec))
            except:
                self.log.exception("Error when trying to determine hardware acceleration support.")

        preopts.extend(self.settings.preopts)
        postopts.extend(self.settings.postopts)

        # HEVC Tagging for copied streams
        if info.video.codec in ['x265', 'h265', 'hevc'] and vcodec == 'copy':
            postopts.extend(['-tag:v', 'hvc1'])
            self.log.info("Tagging copied video stream as hvc1")

        return options, preopts, postopts, ripsubopts, downloaded_subs

    def validLanguage(self, language, whitelist, blocked=[]):
        return ((len(whitelist) < 1 or language in whitelist) and language not in blocked)

    def setAcceleration(self, video_codec):
        opts = []
        # Look up which codecs and which decoders/encoders are available in this build of ffmpeg
        codecs = self.converter.ffmpeg.codecs

        # Lookup which hardware acceleration platforms are available in this build of ffmpeg
        hwaccels = self.converter.ffmpeg.hwaccels

        # Find the first of the specified hardware acceleration platform that is available in this build of ffmpeg.  The order of specified hardware acceleration platforms determines priority.
        for hwaccel in self.settings.hwaccels:
            if hwaccel in hwaccels:
                self.log.info("%s hwaccel is supported by this ffmpeg build and will be used [hwaccels]." % hwaccel)
                opts.extend(['-hwaccel', hwaccel])

                # If there's a decoder for this acceleration platform, also use it
                decoder = self.converter.ffmpeg.hwaccel_decoder(video_codec, hwaccel)
                if (decoder in codecs[video_codec]['decoders'] and decoder in self.settings.hwaccel_decoders):
                    self.log.info("%s decoder is also supported by this ffmpeg build and will also be used [hwaccel-decoders]." % decoder)
                    opts.extend(['-vcodec', decoder])
                break
        return opts

    def setDefaultAudioStream(self, audio_settings):
        if len(audio_settings) > 0:
            audio_streams = sorted(audio_settings, key=lambda x: x.get('channels', 1), reverse=self.settings.default_more_channels)
            audio_streams = sorted(audio_streams, key=lambda x: '+comment' in (x.get('disposition') or ''))
            preferred_language_audio_streams = [x for x in audio_streams if x.get('language') == self.settings.adl] if self.settings.adl else audio_streams
            default_stream = audio_streams[0]
            default_streams = [x for x in audio_streams if '+default' in (x.get('disposition') or '')]
            default_preferred_language_streams = [x for x in default_streams if x.get('language') == self.settings.adl] if self.settings.adl else default_streams
            default_streams_not_in_preferred_language = [x for x in default_streams if x not in default_preferred_language_streams]

            self.log.debug("%d total audio streams with %d set to default disposition. %d defaults in your preferred language (%s), %d in other languages." % (len(audio_streams), len(default_streams), len(default_preferred_language_streams), self.settings.adl, len(default_streams_not_in_preferred_language)))
            if len(preferred_language_audio_streams) < 1:
                self.log.debug("No audio streams in your preferred language, using other languages to determine default stream.")

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
                        if remove.get('disposition'):
                            remove['disposition'] = remove.get('disposition').replace('+default', '-default')
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
                    if remove.get('disposition'):
                        remove['disposition'] = remove.get('disposition').replace('+default', '-default')
            if default_stream.get('disposition'):
                default_stream['disposition'] = default_stream.get('disposition').replace('-default', '+default')
                if '+default' not in default_stream.get('disposition'):
                    default_stream['disposition'] += "+default"
            else:
                default_stream['disposition'] = "+default"

            self.log.info("Default audio stream set to %s %s %s channel stream [default-more-channels: %s]." % (default_stream['language'], default_stream['codec'], default_stream['channels'], self.settings.default_more_channels))
        else:
            self.log.debug("Audio output is empty, unable to set default audio streams.")

    def setDefaultSubtitleStream(self, subtitle_settings):
        if len(subtitle_settings) > 0 and self.settings.sdl:
            if len([x for x in subtitle_settings if '+default' in (x.get('disposition') or '')]) < 1:
                default_stream = [x for x in subtitle_settings if x.get('language') == self.settings.sdl][0]

                if default_stream.get('disposition'):
                    default_stream['disposition'] = default_stream.get('disposition').replace('-default', '+default')
                    if '+default' not in default_stream.get('disposition'):
                        default_stream['disposition'] += '+default'
                else:
                    default_stream['disposition'] = '+default'

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
                        streams.sort(key=lambda x: languages.index(x.get('language')) if x.get('language') in languages else 999)
                else:
                    streams.sort(key=lambda x: x.audio_channels, reverse=self.settings.prefer_more_channels)
                    if languages:
                        streams.sort(key=lambda x: languages.index(x.metadata.get('language')) if x.metadata.get('language') in languages else 999)
                    streams.sort(key=lambda x: x.disposition.get('comment'))

    def checkDisposition(self, allowed, source):
        for a in allowed:
            if not source.get(a):
                return False
        return True

    def dispoStringToDict(self, dispostr):
        dispo = {}
        if dispostr:
            d = re.findall('([+-][a-zA-Z]*)', dispostr)
            for x in d:
                dispo[x[1:]] = x.startswith('+')
        return dispo

    def burnSubtitleFilter(self, inputfile, subtitle_streams, swl, valid_external_subs=None):
        if self.settings.burn_subtitles:
            subtitle_streams = [x for x in subtitle_streams if self.validLanguage(x.metadata.get('language'), swl)]
            subtitle_streams = sorted(subtitle_streams, key=lambda x: swl.index(x.metadata.get('language')) if x.metadata.get('language') in swl else 999)
            sub_candidates = []
            if len(subtitle_streams) > 0:
                first_index = sorted([x.index for x in subtitle_streams])[0]

                # Filter subtitles to be burned based on setting
                sub_candidates = [x for x in subtitle_streams if self.checkDisposition(self.settings.burn_dispositions, x.disposition)]
                # Filter out image based subtitles (until we can find a method to get this to work)
                for x in sub_candidates[:]:
                    try:
                        if self.isImageBasedSubtitle(inputfile, x.index):
                            sub_candidates.remove(x)
                    except:
                        self.log.error("Unknown error occurred while trying to determine if subtitle is text or image based. Probably corrupt, skipping.")
                        sub_candidates.remove(x)

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

                # Filter subtitles to be burned based on setting
                sub_candidates = [x for x in valid_external_subs if self.checkDisposition(self.settings.burn_dispositions, x.subtitle[0].disposition)]
                # Filter out image based subtitles (until we can find a method to get this to work)
                for x in sub_candidates[:]:
                    try:
                        if self.isImageBasedSubtitle(x.path, 0):
                            sub_candidates.remove(x)
                    except:
                        self.log.error("Unknown error occurred while trying to determine if subtitle is text or image based. Probably corrupt, skipping.")
                        sub_candidates.remove(x)

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
                if fname.startswith(filename):  # filename in fname:
                    valid_external_sub = self.isValidSubtitleSource(os.path.join(dirName, fname))
                    if valid_external_sub:
                        subname, langext = os.path.splitext(subname)
                        lang = 'und'
                        while langext:
                            lang = getAlpha3TCode(langext)
                            if lang != 'und':
                                break
                            subname, langext = os.path.splitext(subname)
                        if self.settings.sdl and lang == 'und':
                            lang = self.settings.sdl
                        valid_external_sub.subtitle[0].metadata['language'] = lang

                        if self.validLanguage(lang, swl):
                            self.log.debug("External %s subtitle file detected %s." % (lang, fname))
                            for dispo in BaseCodec.DISPOSITIONS:
                                valid_external_sub.subtitle[0].disposition[dispo] = ("." + dispo) in fname
                            valid_external_subs.append(valid_external_sub)
                        else:
                            self.log.debug("Ignoring %s external subtitle stream due to language %s." % (fname, lang))
        self.log.info("Scanned for external subtitles and found %d results in your approved languages." % (len(valid_external_subs)))
        valid_external_subs.sort(key=lambda x: swl.index(x.subtitle[0].metadata['language']) if x.subtitle[0].metadata['language'] in swl else 999)

        return valid_external_subs

    def downloadSubtitles(self, inputfile, existing_subtitle_streams, swl, original=None):
        if self.settings.downloadsubs:
            languages = set()
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
                return []

            self.log.info("Attempting to download subtitles.")

            # Attempt to set the dogpile cache
            try:
                subliminal.region.configure('dogpile.cache.memory')
            except:
                pass

            try:
                video = subliminal.scan_video(os.path.abspath(inputfile))
                if self.settings.ignore_embedded_subs:
                    video.subtitle_languages = set()
                else:
                    video.subtitle_languages = set([Language(x.metadata['language']) for x in existing_subtitle_streams])

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
        return []

    def setPermissions(self, path):
        try:
            os.chmod(path, self.settings.permissions.get('chmod', int('0664', 8)))
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
        return self.getSubOutputFile(inputfile, language, options['disposition'], extension)

    def getSubOutputFile(self, inputfile, language, disposition, extension):
        disposition = self.dispoStringToDict(disposition)
        dispo = ""
        for k in disposition:
            if disposition[k] and k in self.settings.filename_dispositions:
                dispo += "." + k
        input_dir, filename, input_extension = self.parseFile(inputfile)
        output_dir = self.settings.output_dir or input_dir
        outputfile = os.path.join(output_dir, filename + "." + language + dispo + "." + extension)

        i = 2
        while os.path.isfile(outputfile):
            self.log.debug("%s exists, appending %s to filename." % (outputfile, i))
            outputfile = os.path.join(output_dir, filename + "." + language + dispo + "." + str(i) + "." + extension)
            i += 1
        return outputfile

    def ripSubs(self, inputfile, ripsubopts):
        rips = []
        for options in ripsubopts:
            extension = self.getSubExtensionFromCodec(options['format'])
            outputfile = self.getSubOutputFileFromOptions(inputfile, options, extension)

            try:
                self.log.info("Ripping %s subtitle from source stream %s into external file." % (options["language"], options['index']))
                conv = self.converter.convert(outputfile, options, timeout=None)
                for timecode in conv:
                    pass

                self.log.info("%s created." % outputfile)
                rips.append(outputfile)
            except (FFMpegConvertError, ConverterError):
                self.log.error("Unable to create external %s subtitle file for stream %s, may be an incompatible format." % (extension, options['index']))
                self.removeFile(outputfile)
                continue
            except:
                self.log.exception("Unable to create external subtitle file for stream %s." % (options['index']))
            self.setPermissions(outputfile)
        return rips

    def getOutputFile(self, input_dir, filename, input_extension, temp_extension=None, number=0):
        output_dir = self.settings.output_dir or input_dir
        output_extension = temp_extension or self.settings.output_extension

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
        return False

    def canBypassConvert(self, inputfile, info):
        # Process same extensions
        if self.settings.output_extension == self.parseFile(inputfile)[2]:
            if not self.settings.force_convert and not self.settings.process_same_extensions:
                self.log.info("Input and output extensions are the same so passing back the original file [process-same-extensions: %s]." % self.settings.process_same_extensions)
                return True
            elif info.format.metadata.get('encoder', '').startswith('sma') and not self.settings.force_convert:
                self.log.info("Input and output extensions match and the file appears to have already been processed by SMA, enable force-convert to override [force-convert: %s]." % self.settings.force_convert)
                return True
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
                    self.displayProgressBar(timecode)
            if reportProgress:
                self.displayProgressBar(100, newline=True)

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
            try:
                os.rename(inputfile, originalinputfile)
                return None, originalinputfile
            except:
                self.log.exception("Error restoring original inputfile after exception.")
                return None, inputfile
        except:
            self.log.exception("Unexpected exception during conversion.")
            try:
                os.rename(inputfile, originalinputfile)
                return None, originalinputfile
            except:
                self.log.exception("Error restoring original inputfile after FFMPEG error.")
                return None, inputfile

        # Check if the finaloutputfile differs from the outputfile. This can happen during above renaming or from temporary extension option
        if outputfile != finaloutputfile:
            self.log.debug("Outputfile and finaloutputfile are different attempting to rename to final extension [temp_extension].")
            try:
                os.rename(outputfile, finaloutputfile)
            except:
                self.log.exception("Unable to rename output file to its final destination file extension [temp_extension].")
                finaloutputfile = outputfile

        return finaloutputfile, inputfile

    def displayProgressBar(self, complete, width=20, newline=False):
        try:
            divider = 100 / width

            if complete > 100:
                complete = 100

            sys.stdout.write('\r')
            sys.stdout.write('[{0}] {1}%'.format('#' * int(round(complete / divider)) + ' ' * int(round(width - (complete / divider))), complete))
            if newline:
                sys.stdout.write('\n')
            sys.stdout.flush()
            self.log.debug(complete)
        except:
            print(complete)

    # Break apart a file path into the directory, filename, and extension
    def parseFile(self, path):
        path = os.path.abspath(path)
        input_dir, filename = os.path.split(path)
        filename, input_extension = os.path.splitext(filename)
        input_extension = input_extension[1:]
        return input_dir, filename, input_extension.lower()

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
                self.log.warning("QT FastStart did not run - perhaps moov atom was at the start already or file is in the wrong format.")
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
                if replacement:
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
