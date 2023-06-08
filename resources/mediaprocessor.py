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
from resources.extensions import subtitle_codec_extensions, bad_sub_extensions
from resources.metadata import Metadata, MediaType
from resources.postprocess import PostProcessor
from resources.lang import getAlpha3TCode
from autoprocess import plex
try:
    import cleanit
except ImportError:
    cleanit = None
try:
    from ffsubsync import ffsubsync
except ImportError:
    ffsubsync = None
try:
    import subliminal
    from guessit import guessit
    from babelfish import Language
except ImportError:
    subliminal = None
    guessit = None
    Language = None

# Custom Functions
from resources.custom import *


class MediaProcessor:
    default_channel_bitrate = 128

    def __init__(self, settings, logger=None):
        self.log = logger or logging.getLogger(__name__)
        self.settings = settings
        self.converter = Converter(settings.ffmpeg, settings.ffprobe)
        self.deletesubs = set()

    def fullprocess(self, inputfile, mediatype, reportProgress=False, original=None, info=None, tmdbid=None, tvdbid=None, imdbid=None, season=None, episode=None, language=None, tagdata=None, post=True):
        try:
            info = self.isValidSource(inputfile, tagdata=tagdata)
            if info:
                self.log.info("Processing %s." % inputfile)

                try:
                    tagdata = tagdata or Metadata(mediatype, tvdbid=tvdbid, tmdbid=tmdbid, imdbid=imdbid, season=season, episode=episode, original=original, language=language)
                    tmdbid = tagdata.tmdbid
                except KeyboardInterrupt:
                    raise
                except:
                    self.log.exception("Unable to get metadata.")
                    tagdata = None

                output = self.process(inputfile, original=original, info=info, tagdata=tagdata, reportProgress=reportProgress)

                if output:
                    if not language:
                        language = self.settings.taglanguage or self.getDefaultAudioLanguage(output["options"]) or None
                    self.log.debug("Tag language setting is %s, using language %s for tagging." % (self.settings.taglanguage or None, language))
                    # Tag with metadata
                    tagfailed = False
                    if self.settings.tagfile and tagdata:
                        try:
                            self.log.info("Tagging %s with TMDB ID %s." % (inputfile, tagdata.tmdbid))
                            tagdata.writeTags(output['output'], inputfile, self.converter, self.settings.artwork, self.settings.thumbnail, output['x'], output['y'], streaming=output['rsi'])
                        except KeyboardInterrupt:
                            raise
                        except:
                            self.log.exception("Unable to tag file")
                            tagfailed = True

                    # QTFS
                    if self.settings.relocate_moov and not tagfailed:
                        self.QTFS(output['output'])

                    # Reverse Ouput
                    output['output'] = self.restoreFromOutput(inputfile, output['output'])
                    for i, sub in enumerate(output['external_subs']):
                        output['external_subs'][i] = self.restoreFromOutput(inputfile, sub)

                    # Copy to additional locations
                    output_files = self.replicate(output['output'])
                    for sub in [x for x in output['external_subs'] if os.path.exists(x)]:
                        output_files.extend(self.replicate(sub))

                    for file in output_files:
                        self.setPermissions(file)

                    if post:
                        self.post(output_files, mediatype, tmdbid=tmdbid, season=season, episode=episode)

                    return output_files
            else:
                self.log.info("File %s is not valid" % inputfile)
        except KeyboardInterrupt:
            raise
        except:
            self.log.exception("Error processing")
        return False

    def post(self, output_files, mediatype, tvdbid=None, tmdbid=None, imdbid=None, season=None, episode=None):
        if self.settings.postprocess:
            if not tmdbid:
                try:
                    tagdata = Metadata(mediatype, tvdbid=tvdbid, tmdbid=tmdbid, imdbid=imdbid, season=season, episode=episode)
                    tmdbid = tagdata.tmdbid
                except KeyboardInterrupt:
                    raise
                except:
                    self.log.exception("Unable to get metadata.")
                    tagdata = None

            # Run any post process scripts
            postprocessor = PostProcessor(output_files, self.log, wait=self.settings.waitpostprocess)
            postprocessor.setEnv(mediatype, tmdbid, season, episode)
            postprocessor.run_scripts()

        # Refresh Plex
        if self.settings.Plex.get('refresh', False):
            try:
                plex.refreshPlex(self.settings, output_files[0], self.log)
            except KeyboardInterrupt:
                raise
            except:
                self.log.exception("Error refreshing Plex.")

    # Process a file from start to finish, with checking to make sure formats are compatible with selected settings
    def process(self, inputfile, reportProgress=False, original=None, info=None, progressOutput=None, tagdata=None):
        self.log.debug("Process started.")

        delete = self.settings.delete
        deleted = False
        options = None
        preopts = None
        postopts = None
        outputfile = None
        ripped_subs = []
        downloaded_subs = []

        info = info or self.isValidSource(inputfile, tagdata=tagdata)

        self.settings.output_dir = self.settings.output_dir if self.outputDirHasFreeSpace(inputfile) else None

        if info:
            try:
                options, preopts, postopts, ripsubopts, downloaded_subs = self.generateOptions(inputfile, info=info, original=original, tagdata=tagdata)
            except KeyboardInterrupt:
                raise
            except:
                self.log.exception("Unable to generate options, unexpected exception occurred.")
                return None
            if self.canBypassConvert(inputfile, info, options):
                outputfile = inputfile
                self.log.info("Bypassing conversion and setting outputfile to inputfile.")
            else:
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
                except KeyboardInterrupt:
                    raise
                except:
                    self.log.exception("Unable to log options.")

                ripped_subs = self.ripSubs(inputfile, ripsubopts)
                for rs in ripped_subs:
                    self.cleanExternalSub(rs)
                try:
                    outputfile, inputfile = self.convert(options, preopts, postopts, reportProgress, progressOutput)
                except KeyboardInterrupt:
                    raise
                except:
                    self.log.exception("Unexpected exception encountered during conversion")
                    return None

            if not outputfile:
                self.log.debug("Error converting, no outputfile generated for inputfile %s." % inputfile)
                return None

            self.log.debug("%s created from %s successfully." % (outputfile, inputfile))

            if outputfile == inputfile:
                if self.settings.output_dir:
                    try:
                        outputfile = os.path.join(self.settings.output_dir, os.path.split(inputfile)[1])
                        self.log.debug("Outputfile set to %s." % outputfile)
                        shutil.copy(inputfile, outputfile)
                    except KeyboardInterrupt:
                        raise
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

            rsi = 0
            if self.settings.output_format in ['mkv'] and self.settings.relocate_moov:
                self.log.debug("Relocate MOOV enabled but format is %s, adding reserve_index_space parameter.")
                rsi = info.format.duration / (60 * 60)
                rsi = int(rsi) if rsi == int(rsi) else int(rsi) + 1
                rsi = rsi * 50

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
                    'y': dim['y'],
                    'rsi': rsi
                    }
        return None

    # Wipe disposition data based on settings
    def cleanDispositions(self, info):
        for stream in info.streams:
            for dispo in self.settings.sanitize_disposition:
                self.log.debug("Setting %s to False for stream %d [sanitize-disposition]." % (dispo, stream.index))
                stream.disposition[dispo] = False

    # Get title for video stream based on disposition
    def videoStreamTitle(self, stream, options, hdr=False, tagdata=None):
        width = options.get("width", 0)
        height = options.get("height", 0)
        if not width and not height:
            width = stream.video_width or 0
            height = stream.video_height or 0

        if streamTitle:
            try:
                customTitle = streamTitle(self, stream, options, hdr=hdr, tagdata=tagdata)
                if customTitle is not None:
                    return customTitle
            except:
                self.log.exception("Custom streamTitle exception")

        if self.settings.keep_titles and stream.metadata.get('title'):
            return stream.metadata.get('title')

        output = "Video"

        if width >= 7600 or height >= 4300:
            output = "8K"
        elif width >= 3800 or height >= 2100:
            output = "4K"
        elif width >= 1900 or height >= 1060:
            output = "FHD"
        elif width >= 1260 or height >= 700:
            output = "HD"
        else:
            output = "SD"

        if hdr:
            output += " HDR"
        return output.strip() if output else None

    # Get title for audio stream based on disposition
    def audioStreamTitle(self, stream, options, tagdata=None):
        if streamTitle:
            try:
                customTitle = streamTitle(self, stream, options, tagdata=tagdata)
                if customTitle is not None:
                    return customTitle
            except:
                self.log.exception("Custom streamTitle exception")

        if self.settings.keep_titles and stream.metadata.get('title'):
            return stream.metadata.get('title')

        channels = options.get("channels", 0)
        output = "Audio"
        if channels == 1:
            output = "Mono"
        elif channels == 2:
            output = "Stereo"
        elif channels > 2:
            output = "%d.1 Channel" % (channels - 1)

        disposition = stream.disposition
        for dispo in BaseCodec.DISPO_STRINGS:
            if disposition.get(dispo):
                output += " (%s)" % BaseCodec.DISPO_STRINGS[dispo]
        return output.strip() if output else None

    # Get title for subtitle stream based on disposition
    def subtitleStreamTitle(self, stream, options, imageBased=False, path=None, tagdata=None):
        if streamTitle:
            try:
                customTitle = streamTitle(self, stream, options, imageBased=imageBased, path=path, tagdata=None)
                if customTitle is not None:
                    return customTitle
            except:
                self.log.exception("Custom streamTitle exception")

        if self.settings.keep_titles and stream.metadata.get('title'):
            return stream.metadata.get('title')

        output = ""
        disposition = stream.disposition
        for dispo in BaseCodec.DISPO_STRINGS:
            if disposition.get(dispo):
                output += "%s " % BaseCodec.DISPO_STRINGS[dispo]
        return output.strip() if output else None

    # Determine if a file can be read by FFPROBE
    def isValidSource(self, inputfile, tagdata=None):
        try:
            extension = self.parseFile(inputfile)[2]
            if extension in self.settings.ignored_extensions:
                self.log.debug("Invalid source, extension is blacklisted [ignored-extensions].")
                return None
            if self.settings.minimum_size > 0 and os.path.getsize(inputfile) < (self.settings.minimum_size * 1000000):
                self.log.debug("Invalid source, below minimum size threshold [minimum-size].")
                return None
            info = self.converter.probe(inputfile)
            if not info:
                self.log.debug("Invalid source, no data returned.")
                return None
            if not info.video:
                self.log.debug("Invalid source, no video stream detected.")
                return None
            if not info.audio or len(info.audio) < 1:
                self.log.debug("Invalid source, no audio stream detected.")
                return None
            if validation:
                try:
                    if not validation(self, info, inputfile, tagdata):
                        self.log.debug("Failed custom validation check, file is not valid.")
                        return None
                except KeyboardInterrupt:
                    raise
                except:
                    self.log.exception("Custom validation check error.")
            return info
        except KeyboardInterrupt:
            raise
        except:
            self.log.exception("isValidSource unexpectedly threw an exception, returning None.")
            return None

    # Determine if a file can be read by FFPROBE and is a subtitle only
    def isValidSubtitleSource(self, inputfile):
        _, _, extension = self.parseFile(inputfile)
        if extension in bad_sub_extensions or extension in self.settings.ignored_extensions:
            return None
        try:
            info = self.converter.probe(inputfile)
            if info:
                if len(info.subtitle) < 1 or info.video or len(info.audio) > 0:
                    return None
            return info
        except KeyboardInterrupt:
            raise
        except:
            self.log.exception("isValidSubtitleSource unexpectedly threw an exception, returning None.")
            return None

    # Parse filename of external subtitle file and set appropriate disposition and language information
    def processExternalSub(self, valid_external_sub, inputfile):
        if not valid_external_sub:
            return valid_external_sub
        _, filename, _ = self.parseFile(inputfile)
        _, subname, _ = self.parseFile(valid_external_sub.path)
        subname = subname[len(filename + os.path.extsep):]
        lang = BaseCodec.UNDEFINED
        for suf in subname.lower().split(os.path.extsep):
            self.log.debug("Processing subtitle file suffix %s." % (suf))
            l = getAlpha3TCode(suf)
            if lang == BaseCodec.UNDEFINED and l != BaseCodec.UNDEFINED:
                lang = l
                self.log.debug("Found language match %s." % (lang))
                continue
            dsuf = BaseCodec.DISPO_ALTS.get(suf, suf)
            if dsuf in BaseCodec.DISPOSITIONS:
                valid_external_sub.subtitle[0].disposition[dsuf] = True
                self.log.debug("Found disposition match %s." % (suf))
        if self.settings.sdl and lang == BaseCodec.UNDEFINED:
            lang = self.settings.sdl
        valid_external_sub.subtitle[0].metadata['language'] = lang
        return valid_external_sub

    # Default audio language based on encoder options
    def getDefaultAudioLanguage(self, options):
        if isinstance(options, dict):
            for a in options.get("audio", []):
                if "+default" in a.get("disposition", "").lower():
                    self.log.debug("Default audio language is %s." % a.get("language"))
                    return a.get("language")
        else:
            for a in options.audio:
                if a.disposition.get("default"):
                    self.log.debug("Default audio language is %s." % a.metadata.get("language"))
                    return a.metadata.get("language")
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
    def estimateVideoBitrate(self, info, baserate=64000, tolerance=0.95):
        # attempt to return the detected video bitrate, if applicable
        min_video_bitrate = (info.video.bitrate / 1000) if info.video and info.video.bitrate else None

        try:
            total_bitrate = info.format.bitrate
            audio_bitrate = 0
            min_audio_bitrate = 0
            for a in info.audio:
                audio_bitrate += a.bitrate if a.bitrate else (baserate * (a.audio_channels or 2))

            self.log.debug("Total bitrate is %s." % info.format.bitrate)
            self.log.debug("Total audio bitrate is %s." % audio_bitrate)
            audio_bitrate += min_audio_bitrate
            calculated_bitrate = (total_bitrate - audio_bitrate) / 1000
            self.log.debug("Estimated video bitrate is %s." % (calculated_bitrate * 1000))
            return min_video_bitrate if min_video_bitrate and min_video_bitrate < (calculated_bitrate * tolerance) else (calculated_bitrate * tolerance)
        except:
            if info.format.bitrate:
                return min_video_bitrate if min_video_bitrate and min_video_bitrate < (info.format.bitrate / 1000) else (info.format.bitrate / 1000)
        return min_video_bitrate

    # Generate a JSON formatter dataset with the input and output information and ffmpeg command for a theoretical conversion
    def jsonDump(self, inputfile, original=None, tagdata=None):
        dump = {}
        dump["input"], info = self.generateSourceDict(inputfile, tagdata)
        dump["output"], dump["preopts"], dump["postopts"], dump["ripsubopts"], dump["downloadedsubs"] = self.generateOptions(inputfile, info=info, original=original, tagdata=tagdata)
        if self.canBypassConvert(inputfile, info, dump["output"]):
            dump["output"] = dump["input"]
            dump["output"]["bypassConvert"] = True
            dump["preopts"] = None
            dump["postopts"] = None
            dump["ripsubopts"] = None
            dump["downloadedsubs"] = None
        else:
            parsed = self.converter.parse_options(dump["output"])
            input_dir, filename, input_extension = self.parseFile(inputfile)
            outputfile, _ = self.getOutputFile(input_dir, filename, input_extension)
            cmds = self.converter.ffmpeg.generateCommands(outputfile, parsed, dump["preopts"], dump["postopts"])
            dump["ffmpeg_commands"] = []
            dump["ffmpeg_commands"].append(" ".join("\"%s\"" % item if " " in item and "\"" not in item else item for item in cmds))
            for suboptions in dump["ripsubopts"]:
                subparsed = self.converter.parse_options(suboptions)
                extension = self.getSubExtensionFromCodec(suboptions['format'])
                suboutputfile = self.getSubOutputFileFromOptions(inputfile, suboptions, extension)
                subcmds = self.converter.ffmpeg.generateCommands(suboutputfile, subparsed)
                dump["ffmpeg_commands"].append(" ".join(str(item) for item in subcmds))
            for sub in dump["downloadedsubs"]:
                self.log.debug("Cleaning up downloaded sub %s which was only used to simulate options." % (sub))
                self.removeFile(sub)

        return json.dumps(dump, sort_keys=False, indent=4).replace("\\\\", "\\").replace("\\\"", "\"")

    # Generate a dict of data about a source file
    def generateSourceDict(self, inputfile, tagdata=None):
        output = {}
        _, _, input_extension = self.parseFile(inputfile)
        output['extension'] = input_extension
        probe = self.isValidSource(inputfile, tagdata)
        self.titleDispositionCheck(probe)
        if probe:
            output.update(probe.json)
        else:
            output['error'] = "Invalid input, unable to read"
        return output, probe

    # Pass over audio and subtitle streams to ensure the language properties are safe, return any adjustments made to SWL/AWL
    def safeLanguage(self, info, tagdata=None):
        awl = self.settings.awl
        original_language = None
        if self.settings.audio_original_language and tagdata:
            try:
                original_language = tagdata.original_language
                if original_language not in awl:
                    self.log.debug("Appending %s to allowed audio languages [include-original-language]." % (original_language))
                    awl.append(original_language)
                    self.settings.adl = self.settings.adl or original_language
            except KeyboardInterrupt:
                raise
            except:
                self.log.exception("Exception while trying to determine original language [include-original-language].")

        swl = self.settings.swl
        if self.settings.subtitle_original_language and tagdata:
            try:
                original_language = tagdata.original_language
                if original_language not in swl:
                    self.log.debug("Appending %s to allowed subtitle languages [include-original-language]." % (original_language))
                    swl.append(original_language)
                    self.settings.sdl = self.settings.sdl or original_language
            except KeyboardInterrupt:
                raise
            except:
                self.log.exception("Exception while trying to determine original language [include-original-language].")

        # Loop through audio streams and clean up language metadata by standardizing undefined languages and applying the ADL setting
        for a in info.audio:
            a.metadata['language'] = getAlpha3TCode(a.metadata.get('language'), self.settings.adl)

        if len(awl) > 0 and not any(a.metadata.get('language') in awl and self.validDisposition(a, self.settings.ignored_audio_dispositions) for a in info.audio):
            self.log.debug("No valid audio tracks found, relaxing audio language restrictions.")
            awl = []

        # Prep subtitle streams by cleaning up languages and setting SDL
        for s in info.subtitle:
            s.metadata['language'] = getAlpha3TCode(s.metadata.get('language'), self.settings.sdl)
        return awl, swl

    # Check and see if clues about the disposition are in the title
    def titleDispositionCheck(self, info):
        DISPO_MAP = {
            'comment': 'comment',
            'hearing': 'hearing_impaired',
            'sdh': 'hearing_impaired',
            'visual': 'visual_impaired',
            'forced': 'forced'
        }

        for stream in info.streams:
            title = stream.metadata.get('title', '').lower()
            for k in DISPO_MAP:
                if k in title:
                    stream.disposition[DISPO_MAP[k]] = True
                    self.log.debug("Found %s in stream title, setting %s disposition to True." % (k, DISPO_MAP[k]))

    # Get source audio tracks that meet criteria for being the same based on codec combination, language, and dispostion
    def mapStreamCombinations(self, audiostreams):
        combinations = []
        for combo in self.settings.stream_codec_combinations:
            indexes = self.sublistIndexes([x.codec for x in audiostreams], combo)
            self.log.debug("Found indexes %s where codec parameters matched combination %s" % (indexes, combo))
            for index in indexes:
                stream_sublist = audiostreams[index: index + len(combo)]
                language_sublist = [x.metadata['language'] for x in stream_sublist]
                dispo_sublist = [dict(x.disposition) for x in stream_sublist]
                for x in dispo_sublist:
                    x['default'] = False
                same_language = all(x == language_sublist[0] for x in language_sublist)
                same_dispo = all(x == dispo_sublist[0] for x in dispo_sublist)
                if same_language and same_dispo:
                    combinations.append([x.index for x in stream_sublist])
        self.log.info("The following stream indexes have been identified as being copies: %s [stream-codec-combinations]." % combinations)
        return combinations

    # Iterate through generated options and remove potential duplicate streams based on mapped combinations
    def purgeDuplicateStreams(self, combinations, options, info, acodecs, uacodecs):
        purge = []
        for combo in combinations:
            filtered_options = [x for x in options if x['map'] in combo]
            channels = sorted(list(set([x['channels'] for x in filtered_options])), reverse=True)
            for c in channels:
                same_channel_options = [x for x in filtered_options if x['channels'] == c]
                if len(same_channel_options) > 1:
                    allowed_codecs = uacodecs if c <= 2 and uacodecs else acodecs
                    if any(x for x in same_channel_options if x['codec'] == 'copy' and self.getSourceStream(x['map'], info).codec in allowed_codecs):
                        # Remuxable stream found but other audio streams of same channel quantity present
                        self.duplicateStreamSort(same_channel_options, info)
                        purge.extend(same_channel_options[1:])
                    else:
                        codecs = [self.getSourceStream(x['map'], info).codec if x['codec'] == 'copy' else x['codec'] for x in same_channel_options]
                        for codec in set(codecs):
                            same_codec_options = [x for x in same_channel_options if Converter.codec_name_to_ffprobe_codec_name(x['codec']) == codec or (x['codec'] == 'copy' and self.getSourceStream(x['map'], info).codec == codec)]
                            if len(same_codec_options) > 1:
                                # No remuxable streams but 2 streams of the output codec are being created
                                self.duplicateStreamSort(same_codec_options, info)
                                purge.extend(same_codec_options[1:])
        self.log.debug("Purging the following streams:")
        self.log.debug(json.dumps(purge, indent=4))
        self.log.info("Found %d streams that can be removed from the output file since they will be duplicates [stream-codec-combinations]." % len(purge))
        for p in purge:
            try:
                options.remove(p)
            except:
                self.log.debug("Unable to purge stream, may already have been removed.")
        return len(purge) > 0

    # Sorter used by purgeDuplicateStreams
    def duplicateStreamSort(self, options, info):
        options.sort(key=lambda x: x['bitrate'], reverse=True)
        options.sort(key=lambda x: self.getSourceStream(x['map'], info).disposition['default'], reverse=True)
        options.sort(key=lambda x: x['codec'] == "copy", reverse=True)

    # Get indexes for sublists
    def sublistIndexes(self, x, y):
        indexes = []
        occ = [i for i, a in enumerate(x) if a == y[0]]
        for b in occ:
            if x[b:b + len(y)] == y:
                indexes.append(b)
        return indexes

    # Ensure ffprobe variant of codec is present
    def ffprobeSafeCodecs(self, codecs):
        if codecs:
            ffpcodec = Converter.codec_name_to_ffprobe_codec_name(codecs[0])
            if ffpcodec and ffpcodec not in codecs:
                self.log.debug("Codec pool is missing the FFPROBE value of the primary conversion codec %s which will prevent remuxing, adding %s to the list." % (codecs[0], ffpcodec))
                codecs.append(ffpcodec)
        return codecs

    # Generate a dict of options to be passed to FFMPEG based on selected settings and the source file parameters and streams
    def generateOptions(self, inputfile, info=None, original=None, tagdata=None):
        # Get path information from the input file
        sources = [inputfile]
        ripsubopts = []

        codecs = self.converter.ffmpeg.codecs
        pix_fmts = self.converter.ffmpeg.pix_fmts

        info = info or self.converter.probe(inputfile)

        if not info:
            self.log.error("FFPROBE returned no value for inputfile %s (exists: %s), either the file does not exist or is not a format FFPROBE can read." % (inputfile, os.path.exists(inputfile)))
            return None, None, None, None, None

        # Update disposition information using titles, requires PyMediaInfo
        self.titleDispositionCheck(info)
        self.cleanDispositions(info)

        # Ensure we have adequate language tracks present, assigned undefined languages to default, relax language parameters if needed
        awl, swl = self.safeLanguage(info, tagdata)

        try:
            self.log.info("Input Data")
            self.log.info(json.dumps(info.json, sort_keys=False, indent=4))
        except:
            self.log.exception("Unable to print input file data")

        ###############################################################
        # Video stream
        ###############################################################
        self.log.info("Reading video stream.")
        self.log.info("Video codec detected: %s." % info.video.codec)
        self.log.info("Pix Fmt: %s." % info.video.pix_fmt)
        self.log.info("Profile: %s." % info.video.profile)

        vdebug = "video"
        vHDR = self.isHDR(info.video)
        if vHDR:
            vdebug = vdebug + ".hdr"

        vcodecs = self.settings.hdr.get('codec', []) if vHDR and len(self.settings.hdr.get('codec', [])) > 0 else self.settings.vcodec
        vcodecs = self.ffprobeSafeCodecs(vcodecs)
        self.log.debug("Pool of video codecs is %s." % (vcodecs))
        vcodec = "copy" if info.video.codec in vcodecs else vcodecs[0]

        # Custom
        try:
            if blockVideoCopy and blockVideoCopy(self, info.video, inputfile):
                self.log.info("Custom video stream copy check is preventing copying the stream.")
                vdebug = vdebug + ".custom"
                vcodec = vcodecs[0]
        except KeyboardInterrupt:
            raise
        except:
            self.log.exception("Custom video stream copy check error.")

        vbitrate_estimate = self.estimateVideoBitrate(info)
        vbitrate_ratio = self.settings.vbitrateratio.get(info.video.codec, self.settings.vbitrateratio.get("*", 1.0))
        vbitrate = vbitrate_estimate * vbitrate_ratio
        self.log.debug("Using video bitrate ratio of %f, which results in %f changing to %f." % (vbitrate_ratio, vbitrate_estimate, vbitrate))
        if self.settings.vmaxbitrate and vbitrate > self.settings.vmaxbitrate:
            self.log.debug("Overriding video bitrate. Codec cannot be copied because video bitrate is too high [video-max-bitrate].")
            vdebug = vdebug + ".max-bitrate"
            vcodec = vcodecs[0]
            vbitrate = self.settings.vmaxbitrate

        vwidth = None
        if self.settings.vwidth and self.settings.vwidth < info.video.video_width:
            self.log.debug("Video width is over the max width, it will be downsampled. Video stream can no longer be copied [video-max-width].")
            vdebug = vdebug + ".max-width"
            vcodec = vcodecs[0]
            vwidth = self.settings.vwidth

        vlevel = self.settings.video_level
        if self.settings.video_level and info.video.video_level and (info.video.video_level > self.settings.video_level):
            self.log.debug("Video level %0.1f. Codec cannot be copied because video level is too high [video-max-level]." % (info.video.video_level))
            vdebug = vdebug + ".max-level"
            vcodec = vcodecs[0]

        vprofile = None
        if vHDR and len(self.settings.hdr.get('profile')) > 0:
            if info.video.profile in self.settings.hdr.get('profile'):
                vprofile = info.video.profile
            else:
                vprofile = self.settings.hdr.get('profile')[0]
                self.log.debug("Overriding video profile. Codec cannot be copied because profile is not approved [hdr-profile].")
                vdebug = vdebug + ".hdr-profile-fmt"
                vcodec = vcodecs[0]
        else:
            if len(self.settings.vprofile) > 0:
                if info.video.profile in self.settings.vprofile:
                    vprofile = info.video.profile
                else:
                    vprofile = self.settings.vprofile[0] if len(self.settings.vprofile) > 0 else None
                    self.log.debug("Video profile is not supported. Video stream can no longer be copied [video-profile].")
                    vdebug = vdebug + ".profile"
                    vcodec = vcodecs[0]

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

        vfilter = self.settings.hdr.get('filter') or None if vHDR else self.settings.vfilter or None
        if vHDR and self.settings.hdr.get('filter') and self.settings.hdr.get('forcefilter'):
            self.log.debug("Video HDR force filter is enabled. Video stream can no longer be copied [hdr-force-filter].")
            vdebug = vdebug + ".hdr-force-filter"
            vcodec = vcodecs[0]
        elif not vHDR and vfilter and self.settings.vforcefilter:
            self.log.debug("Video force filter is enabled. Video stream can no longer be copied [video-force-filter].")
            vfilter = self.settings.vfilter
            vcodec = vcodecs[0]
            vdebug = vdebug + ".force-filter"

        vpreset = self.settings.hdr.get('preset') or None if vHDR else self.settings.preset or None

        vparams = self.settings.codec_params or None
        if vHDR and self.settings.hdr.get('codec_params'):
            vparams = self.settings.hdr.get('codec_params')

        vpix_fmt = None
        if vHDR and len(self.settings.hdr.get('pix_fmt')) > 0:
            if info.video.pix_fmt in self.settings.hdr.get('pix_fmt'):
                vpix_fmt = info.video.pix_fmt if self.settings.keep_source_pix_fmt else self.settings.hdr.get('pix_fmt')[0]
            else:
                vpix_fmt = self.settings.hdr.get('pix_fmt')[0]
                self.log.debug("Overriding video pix_fmt. Codec cannot be copied because pix_fmt is not approved [hdr-pix-fmt].")
                vdebug = vdebug + ".hdr-pix-fmt"
                vcodec = vcodecs[0]
        elif not vHDR and len(self.settings.pix_fmt):
            if info.video.pix_fmt in self.settings.pix_fmt:
                vpix_fmt = info.video.pix_fmt if self.settings.keep_source_pix_fmt else self.settings.pix_fmt[0]
            else:
                vpix_fmt = self.settings.pix_fmt[0]
                self.log.debug("Overriding video pix_fmt. Codec cannot be copied because pix_fmt is not approved [pix-fmt].")
                vdebug = vdebug + ".pix_fmt"
                vcodec = vcodecs[0]

        # Bit depth pix-fmt safety check
        source_bit_depth = pix_fmts.get(info.video.pix_fmt, 0)
        output_bit_depth = pix_fmts.get(vpix_fmt, 0)
        bit_depth = output_bit_depth or source_bit_depth
        self.log.debug("Source bit-depth %d, output %d, using depth %d." % (source_bit_depth, output_bit_depth, bit_depth))

        if vcodec != 'copy':
            vencoder = Converter.encoder(vcodec)
            if vencoder and not vencoder.supportsBitDepth(bit_depth):
                self.log.debug("Selected video encoder %s does not support bit depth %d." % (vcodec, bit_depth))
                vpix_fmt = None
                viable_formats = sorted([x for x in pix_fmts if pix_fmts[x] <= vencoder.max_depth], key=lambda x: pix_fmts[x], reverse=True)
                match = re.search(r"yuv[a-z]?[0-9]{3}", info.video.pix_fmt)
                if match:
                    vpix_fmt = next((x for x in viable_formats if match.group(0) in x), None)
                if vpix_fmt:
                    self.log.info("Pix-fmt adjusted to %s in order to maintain compatible bit-depth <=%d." % (vpix_fmt, vencoder.max_depth))
                else:
                    self.log.debug("No viable pix-fmt option found for bit-depth %d, leave as %s." % (vencoder.max_depth, vpix_fmt))

        vframedata = self.normalizeFramedata(info.video.framedata, vHDR) if self.settings.dynamic_params else None
        if vpix_fmt and vframedata and "pix_fmt" in vframedata and vframedata["pix_fmt"] != vpix_fmt:
            self.log.debug("Pix_fmt is changing, will not preserve framedata")
            vframedata = None

        vbsf = None
        if self.settings.removebvs and self.hasBitstreamVideoSubs(info.video.framedata):
            self.log.debug("Found side data type with closed captioning [remove-bitstream-subs]")
            vbsf = "filter_units=remove_types=6"

        self.log.debug("Video codec: %s." % vcodec)
        self.log.debug("Video bitrate: %s." % vbitrate)
        self.log.debug("Video CRF: %s." % vcrf)
        self.log.debug("Video maxrate: %s." % vmaxrate)
        self.log.debug("Video bufsize: %s." % vbufsize)
        self.log.debug("Video level: %s." % vlevel)
        self.log.debug("Video profile: %s." % vprofile)
        self.log.debug("Video preset: %s." % vpreset)
        self.log.debug("Video pix_fmt: %s." % vpix_fmt)
        self.log.debug("Video field order: %s." % vfieldorder)
        self.log.debug("Video width: %s." % vwidth)
        self.log.debug("Video debug %s." % vdebug)
        self.log.info("Video codec parameters %s." % vparams)
        self.log.info("Creating %s video stream from source stream %d." % (vcodec, info.video.index))

        video_settings = {
            'codec': vcodec,
            'map': info.video.index,
            'bitrate': vbitrate,
            'crf': vcrf,
            'maxrate': vmaxrate,
            'bufsize': vbufsize,
            'level': vlevel,
            'profile': vprofile,
            'preset': vpreset,
            'pix_fmt': vpix_fmt,
            'field_order': vfieldorder,
            'width': vwidth,
            'filter': vfilter,
            'params': vparams,
            'framedata': vframedata,
            'bsf': vbsf,
            'debug': vdebug,
        }
        video_settings['title'] = self.videoStreamTitle(info.video, video_settings, hdr=vHDR, tagdata=tagdata)

        ###############################################################
        # Audio streams
        ###############################################################
        self.log.info("Reading audio streams.")

        # Iterate through audio streams
        audio_settings = []
        blocked_audio_languages = []
        blocked_audio_dispositions = []
        acombinations = self.mapStreamCombinations(info.audio)
        allowua = any(self.settings.ua)

        self.settings.ua = self.ffprobeSafeCodecs(self.settings.ua)
        self.log.debug("Pool universal audio codecs is %s." % (self.settings.ua))

        self.settings.acodec = self.ffprobeSafeCodecs(self.settings.acodec)
        self.log.debug("Pool of audio codecs is %s." % (self.settings.acodec))

        for a in info.audio:
            self.log.info("Audio detected for stream %s - %s %s %d channel." % (a.index, a.codec, a.metadata['language'], a.audio_channels))

            # Custom skip
            try:
                if skipStream and skipStream(self, a, info, inputfile, tagdata):
                    self.log.info("Audio stream %s will be skipped, custom skipStream function returned True." % (a.index))
                    continue
            except KeyboardInterrupt:
                raise
            except:
                self.log.exception("Custom audio stream skip check error for stream %s." % (a.index))

            if self.settings.force_audio_defaults and a.disposition.get('default'):
                self.log.debug("Audio stream %s is flagged as default, forcing inclusion [Audio.force-default]." % (a.index))
            else:
                if not self.validLanguage(a.metadata['language'], awl, blocked_audio_languages):
                    continue
                if not self.validDisposition(a, self.settings.ignored_audio_dispositions, self.settings.unique_audio_dispositions, a.metadata['language'], blocked_audio_dispositions):
                    continue

            try:
                ua = allowua and not (skipUA and skipUA(self, a, info, inputfile, tagdata))
            except KeyboardInterrupt:
                raise
            except:
                ua = allowua
                self.log.exception("Custom skipUA method threw an exception.")

            # Create friendly audio stream if the default audio stream has too many channels
            uadata = None
            if ua and a.audio_channels > 2:
                if self.settings.ua_bitrate == 0:
                    self.log.warning("Universal audio channel bitrate must be greater than 0, defaulting to %d [universal-audio-channel-bitrate]." % self.default_channel_bitrate)
                    self.settings.ua_bitrate = self.default_channel_bitrate
                ua_bitrate = (self.default_channel_bitrate * 2) if (self.settings.ua_bitrate * 2) > (self.default_channel_bitrate * 2) else (self.settings.ua_bitrate * 2)
                ua_disposition = a.dispostr
                ua_filter = self.settings.ua_filter or None
                ua_profile = self.settings.ua_profile or None

                # Custom channel based filters
                ua_afilterchannel = self.settings.afilterchannels.get(a.audio_channels, {}).get(2)
                if ua_afilterchannel:
                    ua_filter = "%s,%s" % (ua_filter, ua_afilterchannel) if ua_filter else ua_afilterchannel
                    self.log.debug("Found an audio filter for converting from %d channels to %d channels. Applying filter %s to UA." % ((a.audio_channels, 2, ua_afilterchannel)))

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
                self.log.debug("Filter: %s." % ua_filter)
                self.log.debug("Bitrate: %s." % ua_bitrate)
                self.log.debug("VBR: %s." % self.settings.ua_vbr)
                self.log.debug("Profile: %s." % ua_profile)
                self.log.debug("Language: %s." % a.metadata['language'])
                self.log.debug("Disposition: %s." % ua_disposition)

                uadata = {
                    'map': a.index,
                    'codec': self.settings.ua[0],
                    'channels': 2,
                    'bitrate': ua_bitrate,
                    'quality': self.settings.ua_vbr,
                    'profile': ua_profile,
                    'samplerate': self.settings.audio_samplerates[0] if len(self.settings.audio_samplerates) > 0 else None,
                    'sampleformat': self.settings.audio_sampleformat,
                    'filter': ua_filter,
                    'language': a.metadata['language'],
                    'disposition': ua_disposition,
                    'debug': 'universal-audio'
                }
                uadata['title'] = self.audioStreamTitle(a, uadata, tagdata=tagdata)

            adebug = "audio"
            # If the universal audio option is enabled and the source audio channel is only stereo, the additional universal stream will be skipped and a single channel will be made regardless of codec preference to avoid multiple stereo channels
            afilter = None
            asample = None
            avbr = None
            adisposition = a.dispostr
            aprofile = None
            if ua and a.audio_channels <= 2:
                self.log.debug("Overriding default channel settings because universal audio is enabled but the source is stereo [universal-audio].")
                acodec = 'copy' if a.codec in self.settings.ua else self.settings.ua[0]
                audio_channels = a.audio_channels
                abitrate = (a.audio_channels * self.default_channel_bitrate) if (a.audio_channels * self.settings.ua_bitrate) > (a.audio_channels * self.default_channel_bitrate) else (a.audio_channels * self.settings.ua_bitrate)
                avbr = self.settings.ua_vbr
                aprofile = self.settings.ua_profile or None
                adebug = "universal-audio"

                # Custom
                try:
                    if blockAudioCopy and blockAudioCopy(self, a, inputfile):
                        self.log.info("Custom audio stream copy check is preventing copying the stream.")
                        adebug = adebug + ".custom"
                        acodec = self.settings.ua[0]
                except KeyboardInterrupt:
                    raise
                except:
                    self.log.exception("Custom audio stream copy check error.")

                # UA Filters
                afilter = self.settings.ua_filter or None
                if afilter and self.settings.ua_forcefilter:
                    self.log.debug("Unable to copy codec because an universal audio filter is set [universal-audio-force-filter].")
                    acodec = self.settings.ua[0]
                    adebug = adebug + ".force-filter"

                # Sample rates
                if len(self.settings.audio_samplerates) > 0 and a.audio_samplerate not in self.settings.audio_samplerates:
                    self.log.debug("Unable to copy codec because audio sample rate %d is not approved [audio-sample-rates]." % (a.audio_samplerate))
                    asample = self.settings.audio_samplerates[0]
                    acodec = self.settings.ua[0]
                    adebug = adebug + ".audio-sample-rates"
            else:
                # If desired codec is the same as the source codec, copy to avoid quality loss
                acodec = 'copy' if a.codec in self.settings.acodec else self.settings.acodec[0]
                avbr = self.settings.avbr
                aprofile = self.settings.aprofile or None
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

                # Custom
                try:
                    if blockAudioCopy and blockAudioCopy(self, a, inputfile):
                        self.log.exception("Custom audio stream copy check is preventing copying the stream.")
                        adebug = adebug + ".custom"
                        acodec = self.settings.acodec[0]
                except KeyboardInterrupt:
                    raise
                except:
                    self.log.exception("Custom audio stream copy check error.")

                # Filters
                afilter = self.settings.afilter or None
                if afilter and self.settings.aforcefilter:
                    self.log.debug("Unable to copy codec because an audio filter is set [audio-force-filter].")
                    acodec = self.settings.acodec[0]
                    adebug = adebug + ".audio-force-filter"

                # Custom channel based filters
                afilterchannel = self.settings.afilterchannels.get(a.audio_channels, {}).get(audio_channels)
                if afilterchannel:
                    afilter = "%s,%s" % (afilter, afilterchannel) if afilter else afilterchannel
                    self.log.debug("Found an audio filter for converting from %d channels to %d channels. Applying filter %s." % (a.audio_channels, audio_channels, afilterchannel))

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
                acodec = self.settings.acodec[0]

            self.log.debug("Audio codec: %s." % acodec)
            self.log.debug("Channels: %s." % audio_channels)
            self.log.debug("Bitrate: %s." % abitrate)
            self.log.debug("VBR: %s." % avbr)
            self.log.debug("Audio Profile: %s." % aprofile)
            self.log.debug("Language: %s." % a.metadata['language'])
            self.log.debug("Filter: %s." % afilter)
            self.log.debug("Disposition: %s." % adisposition)
            self.log.debug("Debug: %s." % adebug)

            # If the ua_first_only option is enabled, disable the ua option after the first audio stream is processed
            if ua and self.settings.ua_first_only:
                self.log.debug("Not creating any additional universal audio streams [universal-audio-first-stream-only].")
                allowua = False

            absf = 'aac_adtstoasc' if acodec == 'copy' and a.codec == 'aac' and self.settings.aac_adtstoasc else None

            self.log.info("Creating %s audio stream from source stream %d." % (acodec, a.index))
            audio_setting = {
                'map': a.index,
                'codec': acodec,
                'channels': audio_channels,
                'bitrate': abitrate,
                'profile': aprofile,
                'quality': avbr,
                'filter': afilter,
                'samplerate': asample,
                'sampleformat': self.settings.audio_sampleformat,
                'language': a.metadata['language'],
                'disposition': adisposition,
                'bsf': absf,
                'debug': adebug
            }
            audio_setting['title'] = self.audioStreamTitle(a, audio_setting, tagdata=tagdata)
            audio_settings.append(audio_setting)

            # Add the universal audio stream
            if uadata:
                self.log.info("Creating %s audio stream from source audio stream %d [universal-audio]." % (uadata.get('codec'), a.index))
                audio_settings.append(uadata)

            # Copy the original stream
            if self.settings.audio_copyoriginal and acodec != 'copy':
                self.log.info("Copying audio stream from source stream %d format %s [audio-copy-original]." % (a.index, a.codec))
                audio_setting = {
                    'map': a.index,
                    'codec': 'copy',
                    'channels': a.audio_channels,
                    'language': a.metadata['language'],
                    'disposition': adisposition,
                    'debug': 'audio-copy-original'
                }
                audio_setting['title'] = self.audioStreamTitle(a, audio_setting, tagdata=tagdata)
                audio_settings.append(audio_setting)

            # Remove the language if we only want the first stream from a given language
            if self.settings.audio_first_language_stream and a.metadata['language'] != BaseCodec.UNDEFINED:
                blocked_audio_languages.append(a.metadata['language'])
                self.log.debug("Blocking further %s audio streams to prevent multiple streams of the same language [audio-first-stream-of-language]." % a.metadata['language'])

        # Purge Duplicate Streams
        self.purgeDuplicateStreams(acombinations, audio_settings, info, self.settings.acodec, self.settings.ua)

        # Audio Sort
        try:
            self.log.debug("Triggering audio track sort [audio.sorting-sorting].")
            audio_settings = self.sortStreams(
                audio_settings,
                self.settings.audio_sorting,
                awl,
                self.settings.audio_sorting_codecs or self.settings.acodec,
                info,
                acombinations,
                tagdata
            )
        except:
            self.log.exception("Error sorting output stream options [audio.sorting-default-sorting].")

        # Set Default Audio Stream
        try:
            self.setDefaultAudioStream(
                self.sortStreams(
                    audio_settings,
                    self.settings.audio_sorting_default,
                    awl,
                    self.settings.audio_sorting_codecs or self.settings.acodec,
                    info,
                    acombinations,
                    tagdata
                )
            )
        except:
            self.log.exception("Unable to set the default audio stream.")

        ###############################################################
        # Subtitle streams
        ###############################################################
        subtitle_settings = []
        blocked_subtitle_languages = []
        blocked_subtitle_dispositions = []
        valid_external_subs = []
        self.log.info("Reading subtitle streams.")
        if not self.settings.ignore_embedded_subs:
            for s in info.subtitle:
                self.log.info("Subtitle detected for stream %s - %s %s." % (s.index, s.codec, s.metadata['language']))
                # Custom skip
                try:
                    if skipStream and skipStream(self, s, info, inputfile, tagdata):
                        self.log.info("Subtitle stream %s will be skipped, custom skipStream function returned True." % (s.index))
                        continue
                except KeyboardInterrupt:
                    raise
                except:
                    self.log.exception("Custom subtitle stream skip check error for stream %s." % (s.index))

                if self.settings.force_subtitle_defaults and s.disposition.get('default'):
                    self.log.debug("Subtitle stream %s is flagged as default, forcing inclusion [Subtitle.force-default]." % (s.index))
                else:
                    if not self.validLanguage(s.metadata['language'], swl, blocked_subtitle_languages):
                        continue
                    if not self.validDisposition(s, self.settings.ignored_subtitle_dispositions, self.settings.unique_subtitle_dispositions, s.metadata['language'], blocked_subtitle_dispositions):
                        continue

                try:
                    image_based = self.isImageBasedSubtitle(inputfile, s.index)
                    self.log.info("Stream %s is %s-based subtitle for codec %s." % (s.index, "image" if image_based else "text", s.codec))
                except KeyboardInterrupt:
                    raise
                except:
                    self.log.error("Unknown error occurred while trying to determine if subtitle is text or image based. Probably corrupt, skipping.")
                    continue

                scodec = None
                if image_based and self.settings.embedimgsubs and self.settings.scodec_image and len(self.settings.scodec_image) > 0:
                    scodec = 'copy' if s.codec in self.settings.scodec_image else self.settings.scodec_image[0]
                elif not image_based and self.settings.embedsubs and self.settings.scodec and len(self.settings.scodec) > 0:
                    if (self.settings.cleanit and cleanit) or (self.settings.ffsubsync and ffsubsync):
                        try:
                            scodec = 'copy' if s.codec in ['srt'] else 'srt'
                            rips = self.ripSubs(inputfile, [self.generateRipSubOpts(inputfile, s, scodec)])
                            if rips:
                                new_sub_path = rips[0]
                                new_sub = self.isValidSubtitleSource(new_sub_path)
                                new_sub = self.processExternalSub(new_sub, inputfile)
                                if new_sub:
                                    self.log.info("Subtitle %s extracted for cleaning/syncing [subtitles.cleanit, subtitles.ffsubsync]." % (new_sub_path))
                                    self.cleanExternalSub(new_sub.path)
                                    self.syncExternalSub(new_sub.path, inputfile)
                                    valid_external_subs.append(new_sub)
                                continue
                        except:
                            self.log.exception("Subtitle rip and cleaning failed.")
                    scodec = 'copy' if s.codec in self.settings.scodec else self.settings.scodec[0]

                if scodec:
                    self.log.info("Creating %s subtitle stream from source stream %d." % (scodec, s.index))
                    subtitle_setting = {
                        'map': s.index,
                        'codec': scodec,
                        'language': s.metadata['language'],
                        'disposition': s.dispostr,
                        'debug': 'subtitle.embed-subs'
                    }
                    subtitle_setting['title'] = self.subtitleStreamTitle(s, subtitle_setting, image_based, tagdata=tagdata)
                    subtitle_settings.append(subtitle_setting)
                    if self.settings.sub_first_language_stream:
                        blocked_subtitle_languages.append(s.metadata['language'])
                else:
                    if image_based and not self.settings.embedimgsubs and self.settings.scodec_image and len(self.settings.scodec_image) > 0:
                        scodec = 'copy' if s.codec in self.settings.scodec_image else self.settings.scodec_image[0]
                    elif not image_based and not self.settings.embedsubs and self.settings.scodec and len(self.settings.scodec) > 0:
                        scodec = 'copy' if s.codec in self.settings.scodec else self.settings.scodec[0]
                    if scodec:
                        ripsubopts.append(self.generateRipSubOpts(inputfile, s, scodec))
                        if self.settings.sub_first_language_stream:
                            blocked_subtitle_languages.append(s.metadata['language'])

        # Attempt to download subtitles if they are missing using subliminal
        downloaded_subs = []
        try:
            downloaded_subs = self.downloadSubtitles(inputfile, info.subtitle, swl, original, tagdata)
        except KeyboardInterrupt:
            raise
        except:
            self.log.exception("Unable to download subitltes [download-subs].")

        ###############################################################
        # External subtitles
        ###############################################################
        if not self.settings.embedonlyinternalsubs:  # Subittles extract just for cleaning will still be imported back
            valid_external_subs = self.scanForExternalSubs(inputfile, swl, valid_external_subs)

        for external_sub in valid_external_subs:
            try:
                image_based = self.isImageBasedSubtitle(external_sub.path, 0)
            except KeyboardInterrupt:
                raise
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
                self.log.info("Skipping external subtitle file %s, no appropriate codecs found or embed disabled." % (os.path.basename(external_sub.path)))
                continue

            if self.settings.force_subtitle_defaults and s.disposition.get('default'):
                self.log.debug("External subtitle %s is flagged as default, forcing inclusion [Subtitle.force-default]." % (os.path.basename(external_sub.path)))
            else:
                if not self.validLanguage(external_sub.subtitle[0].metadata['language'], swl, blocked_subtitle_languages):
                    continue
                if not self.validDisposition(external_sub.subtitle[0], self.settings.ignored_subtitle_dispositions, self.settings.unique_subtitle_dispositions, external_sub.subtitle[0].metadata['language'], blocked_subtitle_dispositions):
                    continue

            if external_sub.path not in sources:
                sources.append(external_sub.path)

            self.log.info("Creating %s subtitle stream by importing %s-based subtitle %s [embed-subs]." % (scodec, "Image" if image_based else "Text", os.path.basename(external_sub.path)))
            subtitle_setting = {
                'source': sources.index(external_sub.path),
                'map': 0,
                'codec': scodec,
                'disposition': sdisposition,
                'language': external_sub.subtitle[0].metadata['language'],
                'debug': 'subtitle.embed-subs'}
            subtitle_setting['title'] = self.subtitleStreamTitle(external_sub.subtitle[0], subtitle_setting, image_based, path=external_sub.path, tagdata=tagdata)
            subtitle_settings.append(subtitle_setting)
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
            vfilter = self.burnSubtitleFilter(inputfile, info, swl, valid_external_subs, tagdata)
        except:
            vfilter = None
            self.log.exception("Encountered an error while trying to determine which subtitle stream for subtitle burn [burn-subtitle].")
        if vfilter:
            self.log.debug("Found valid subtitle stream to burn into video, video cannot be copied [burn-subtitles].")
            video_settings['codec'] = vcodecs[0]
            vcodec = vcodecs[0]
            if video_settings.get('filter'):
                video_settings['filter'] = "%s, %s" % (video_settings['filter'], vfilter)
            else:
                video_settings['filter'] = vfilter
            video_settings['debug'] += ".burn-subtitles"

        # Sort Options
        try:
            subtitle_settings = self.sortStreams(
                subtitle_settings,
                self.settings.sub_sorting,
                swl,
                self.settings.sub_sorting_codecs or (self.settings.scodec + self.settings.scodec_image),
                info,
                tagdata=tagdata
            )
        except:
            self.log.exception("Error sorting output stream options [subtitle.sorting-sorting].")

        # Attachments
        attachments = []
        for f in info.attachment:
            if f.codec in self.settings.attachmentcodec and 'mimetype' in f.metadata and 'filename' in f.metadata:
                attachment = {
                    'map': f.index,
                    'codec': 'copy',
                    'filename': f.metadata['filename'],
                    'mimetype': f.metadata['mimetype']
                }
                attachments.append(attachment)

        # Chapters
        metadata_map = []
        metadata_file = self.scanForExternalMetadata(inputfile)
        if metadata_file:
            self.log.info("Adding metadata file %s to sources and mapping metadata." % (metadata_file))
            sources.append(metadata_file)
            metadata_map = ['-map_chapters', str(sources.index(metadata_file)), '-map_metadata', str(sources.index(metadata_file))]
            if self.settings.strip_metadata:
                self.log.debug("Setting strip-metadata to False since metadata will be coming from external metadata file [strip-metadata].")
                self.settings.strip_metadata = False

        # Collect all options
        options = {
            'source': sources,
            'format': self.settings.output_format,
            'video': video_settings,
            'audio': audio_settings,
            'subtitle': subtitle_settings,
            'attachment': attachments
        }

        if self.settings.subencoding:
            options['sub-encoding'] = self.settings.subencoding

        preopts = []
        postopts = ['-threads', str(self.settings.threads), '-metadata:g', 'encoding_tool=SMA'] + metadata_map

        # FFMPEG allows TrueHD experimental
        if options.get('format') in ['mp4'] and any(a for a in options['audio'] if self.getCodecFromOptions(a, info) == 'truehd'):
            self.log.debug("Adding experimental flag for mp4 with trueHD as a trueHD stream is being copied.")
            postopts.extend(['-strict', 'experimental'])

        if self.isDolbyVision(info.video.framedata):
            postopts.extend(['-strict', 'unofficial'])

        if len(options['subtitle']) > 0:
            self.log.debug("Subtitle streams detected, adding fix_sub_duration option to preopts.")
            preopts.append('-fix_sub_duration')

        if vcodec != 'copy':
            try:
                opts, device = self.setAcceleration(info.video.codec, info.video.pix_fmt, codecs, pix_fmts)
                preopts.extend(opts)
                for k in self.settings.hwdevices:
                    if k in vcodec:
                        match = self.settings.hwdevices[k]
                        self.log.debug("Found a matching device %s for encoder %s [hwdevices]." % (match, vcodec))
                        if not device:
                            self.log.debug("No device was set by the decoder, setting device to %s for encoder %s [hwdevices]." % (match, vcodec))
                            preopts.extend(['-init_hw_device', '%s=sma:%s' % (k, match)])
                            options['video']['device'] = "sma"
                        elif device == match:
                            self.log.debug("Device was already set by the decoder, using same device %s for encoder %s [hwdevices]." % (device, vcodec))
                            options['video']['device'] = "sma"
                        else:
                            self.log.debug("Device was already set by the decoder but does not match encoder, using secondary device %s for encoder %s [hwdevices]." % (match, vcodec))
                            preopts.extend(['-init_hw_device', '%s=sma2:%s' % (k, match)])
                            options['video']['device'] = "sma2"
                            options['video']['decode_device'] = "sma"
                        break
            except KeyboardInterrupt:
                raise
            except:
                self.log.exception("Error when trying to determine hardware acceleration support.")

        preopts.extend(self.settings.preopts)
        postopts.extend(self.settings.postopts)

        # HEVC Tagging for copied streams
        if info.video.codec in ['x265', 'h265', 'hevc'] and vcodec == 'copy':
            postopts.extend(['-tag:v', 'hvc1'])
            self.log.info("Tagging copied video stream as hvc1")

        # Encoder check
        encoders = [item for sublist in [codecs[x]["encoders"] for x in codecs] for item in sublist]
        for o in [video_settings] + audio_settings + subtitle_settings + attachments:
            if 'codec' in o and o['codec'] != 'copy':
                ffcodec = self.converter.codec_name_to_ffmpeg_codec_name(o['codec'])
                if not ffcodec:
                    self.log.warning("===========WARNING===========")
                    self.log.warning("The encoder you have chosen %s is not defined and is not supported by SMA, conversion will likely fail. Please check that this is defined in ./converter/avcodecs.py and if not open a Github feature request to add support." % (o['codec']))
                    self.log.warning("===========WARNING===========")
                elif ffcodec not in encoders and ffcodec != 'copy':
                    self.log.warning("===========WARNING===========")
                    self.log.warning("The encoder you have chosen %s (%s) is not listed as supported in your FFMPEG build, conversion will likely fail, please use a build of FFMPEG that supports %s or choose a different encoder." % (o['codec'], ffcodec, ffcodec))
                    ffpcodec = Converter.codec_name_to_ffprobe_codec_name(o['codec'])
                    if ffpcodec and ffpcodec in codecs and codecs[ffpcodec]['encoders']:
                        self.log.warning("Other encoders your current FFMPEG build does support for codec %s:" % (ffpcodec))
                        self.log.warning(codecs[ffpcodec]['encoders'])
                    self.log.warning("===========WARNING===========")

        return options, preopts, postopts, ripsubopts, downloaded_subs

    # Determine if a stream has a valid language for the main option generator
    def validLanguage(self, language, whitelist, blocked=[]):
        return ((len(whitelist) < 1 or language in whitelist) and language not in blocked)

    # Complex valid disposition checker supporting unique dispositions, language combinations etc for the main option generator
    def validDisposition(self, stream, ignored, unique=False, language='', existing=[], append=True):
        truedispositions = [x for x in stream.disposition if stream.disposition[x]]
        for dispo in truedispositions:
            if BaseCodec.DISPO_ALTS.get(dispo, dispo) in ignored:
                self.log.debug("Ignoring stream because disposition %s is on the ignore list." % (dispo))
                return False
        if unique:
            search = "%s.%s" % (language, stream.dispostr)
            if search in existing:
                self.log.debug("Invalid disposition, stream fitting this disposition profile already exists, ignoring.")
                return False
            if append:
                self.log.debug("Valid disposition, adding %s to the ignored list." % (search))
                existing.append(search)
            return True
        return True

    # Help method to convert dispo string back into a dict
    def dispoStringToDict(self, dispostr):
        dispo = {}
        if dispostr:
            d = re.findall('([+-][a-zA-Z_]*)', dispostr)
            for x in d:
                dispo[x[1:]] = x.startswith('+')
        return dispo

    # Simple disposition filter
    def checkDisposition(self, allowed, source):
        for a in allowed:
            if not source.get(a):
                return False
        return True

    # Hardware acceleration options now with bit depth safety checks
    def setAcceleration(self, video_codec, pix_fmt, codecs=[], pix_fmts=[]):
        opts = []
        pix_fmts = pix_fmts or self.converter.ffmpeg.pix_fmts
        bit_depth = pix_fmts.get(pix_fmt, 0)
        device = None
        # Look up which codecs and which decoders/encoders are available in this build of ffmpeg
        codecs = codecs or self.converter.ffmpeg.codecs

        # Lookup which hardware acceleration platforms are available in this build of ffmpeg
        hwaccels = self.converter.ffmpeg.hwaccels

        self.log.debug("Selected hwaccel options:")
        self.log.debug(self.settings.hwaccels)
        self.log.debug("Selected hwaccel decoder pairs:")
        self.log.debug(self.settings.hwaccel_decoders)
        self.log.debug("FFMPEG hwaccels:")
        self.log.debug(hwaccels)
        self.log.debug("Input format %s bit depth %d." % (pix_fmt, bit_depth))

        # Find the first of the specified hardware acceleration platform that is available in this build of ffmpeg.  The order of specified hardware acceleration platforms determines priority.
        for hwaccel in self.settings.hwaccels:
            if hwaccel in hwaccels:
                device = self.settings.hwdevices.get(hwaccel)
                if device:
                    self.log.debug("Setting hwaccel device to %s." % device)
                    opts.extend(['-init_hw_device', '%s=sma:%s' % (hwaccel, device)])
                    opts.extend(['-hwaccel_device', 'sma'])

                self.log.info("%s hwaccel is supported by this ffmpeg build and will be used [hwaccels]." % hwaccel)
                opts.extend(['-hwaccel', hwaccel])
                if self.settings.hwoutputfmt.get(hwaccel):
                    opts.extend(['-hwaccel_output_format', self.settings.hwoutputfmt[hwaccel]])

                # If there's a decoder for this acceleration platform, also use it
                decoder = self.converter.ffmpeg.hwaccel_decoder(video_codec, self.settings.hwoutputfmt.get(hwaccel, hwaccel))
                self.log.debug("Decoder: %s." % decoder)
                if decoder in codecs[video_codec]['decoders'] and decoder in self.settings.hwaccel_decoders:
                    if Converter.decoder(decoder).supportsBitDepth(bit_depth):
                        self.log.info("%s decoder is also supported by this ffmpeg build and will also be used [hwaccel-decoders]." % decoder)
                        opts.extend(['-vcodec', decoder])
                        self.log.debug("Decoder formats:")
                        self.log.debug(self.converter.ffmpeg.decoder_formats(decoder))
                    else:
                        self.log.debug("Decoder %s is supported but cannot support bit depth %d of format %s." % (decoder, bit_depth, pix_fmt))
                break
        if "-vcodec" not in opts:
            # No matching decoder found for hwaccel, see if there's still a valid decoder that may not match
            for decoder in self.settings.hwaccel_decoders:
                if decoder in codecs[video_codec]['decoders'] and decoder in self.settings.hwaccel_decoders and decoder.startswith(video_codec):
                    if Converter.decoder(decoder).supportsBitDepth(bit_depth):
                        self.log.info("%s decoder is supported by this ffmpeg build and will also be used [hwaccel-decoders]." % decoder)
                        opts.extend(['-vcodec', decoder])
                        self.log.debug("Decoder formats:")
                        self.log.debug(self.converter.ffmpeg.decoder_formats(decoder))
                        break
                    else:
                        self.log.debug("Decoder %s is supported but cannot support bit depth %d of format %s." % (decoder, bit_depth, pix_fmt))
        return opts, device

    # Using sorting and filtering to determine which audio track should be flagged as default, only one track will be selected
    def setDefaultAudioStream(self, audio_streams):
        if audio_streams:
            self.log.debug("Sorting audio streams for default audio stream designation.")
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
                    default_stream['disposition'] += "+defaultDOESTHISEVENWORK"
            else:
                default_stream['disposition'] = "+default"

            self.log.info("Default audio stream set to %s %s %s channel stream [audio-default-sorting: %s]." % (default_stream['language'], default_stream['codec'], default_stream['channels'], self.settings.audio_sorting_default))
        else:
            self.log.debug("Audio output is empty, unable to set default audio streams.")

    # Ensure that at least one subtitle stream is default based on language data
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

    # Returns the sorted source index from a map value, adjusted for stream-codec-combinations
    def getSourceIndexFromMap(self, m, info, combinations):
        m = self.minResolvedMap(m, combinations)
        source = next((s for s in info.streams if s.index == m), None)
        if source:
            return info.streams.index(source)
        return 999

    # Returns a modified map value based on stream-codec-combinations used for sorting
    def minResolvedMap(self, m, combinations):
        combination = next((c for c in combinations if m in c), None)
        if combination:
            return min(combination)
        return m

    # Sort streams
    def sortStreams(self, streams, keys, languages, codecs, info, combinations=[], tagdata=None):
        DISPO_PREFIX = "d."
        ASCENDING_SUFFIX = ".a"
        DESCENDING_SUFFIX = ".d"

        output = streams[:]
        self.log.debug("Sorting streams with keys %s." % (keys))
        original_language = tagdata.original_language if tagdata else None

        SORT_DICT = {
            'codec': lambda x: (codecs.index(self.getCodecFromOptions(x, info)) if (self.getCodecFromOptions(x, info)) in codecs else 999),
            'channels': lambda x: x.get('channels', 999),
            'language': lambda x: languages.index(x.get('language')) if x.get('language') in languages else 999,
            'original-language': lambda x: x.get('language') == original_language,
            'bitrate': lambda x: x.get('bitrate', 999),
            'map': lambda x: self.getSourceIndexFromMap(x['map'], info, combinations),
            'ua': lambda x: "universal-audio" in x.get('debug', ''),
            'original': lambda x: "audio-copy-original" in x.get('debug', '')
        }

        SORT_MEDIASTREAMINFO = {
            'codec': lambda x: codecs.index(x.codec) if x.codec in codecs else 999,
            'channels': lambda x: x.audio_channels,
            'language': lambda x: languages.index(x.metadata.get('language')) if x.metadata.get('language') in languages else 999,
            'original-language': lambda x: x.metadata.get('language') == original_language,
            'bitrate': lambda x: x.bitrate
        }

        if len(streams) > 1:
            for k in keys:
                sort = output[:]
                reverse = False
                if k.endswith(ASCENDING_SUFFIX):
                    reverse = False
                    k = k[:-len(ASCENDING_SUFFIX)]
                elif k.endswith(DESCENDING_SUFFIX):
                    reverse = True
                    k = k[:-len(DESCENDING_SUFFIX)]

                if isinstance(streams[0], dict):
                    if k.startswith(DISPO_PREFIX):
                        disposition = k[len(DISPO_PREFIX):]
                        if disposition:
                            sort.sort(key=lambda x: '+%s' % (disposition) in x.get('disposition', ''), reverse=reverse)
                    elif k in SORT_DICT:
                        sort.sort(key=SORT_DICT[k], reverse=reverse)
                    else:
                        self.log.debug("Skipping sort key %s." % (k))
                        continue
                else:
                    if k.startswith(DISPO_PREFIX):
                        disposition = k[len(DISPO_PREFIX):]
                        disposition = BaseCodec.DISPO_ALTS.get(disposition, disposition)
                        if disposition and disposition in BaseCodec.DISPOSITIONS:
                            sort.sort(key=lambda x: x.disposition.get(disposition), reverse=reverse)
                    elif k in SORT_MEDIASTREAMINFO:
                        sort.sort(key=SORT_MEDIASTREAMINFO[k], reverse=reverse)
                    else:
                        self.log.debug("Skipping sort key %s." % (k))
                        continue
                self.log.debug("Sorted %s with %s:" % ("descending" if reverse else "ascending", k))
                self.log.debug(["%d->%d" % (output.index(x), sort.index(x)) for x in output])
                output = sort

        self.log.info("Final sorting:")
        self.log.info(["%d->%d" % (streams.index(x), output.index(x)) for x in streams])
        return output

    # Generate filter string to burn subtitles
    def burnSubtitleFilter(self, inputfile, info, swl, valid_external_subs=None, tagdata=None):
        if self.settings.burn_subtitles:
            subtitle_streams = info.subtitle
            filtered_subtitle_streams = [x for x in subtitle_streams if self.validLanguage(x.metadata.get('language'), swl) or (self.settings.force_subtitle_defaults and x.disposition.get('default'))]
            filtered_subtitle_streams = sorted(filtered_subtitle_streams, key=lambda x: swl.index(x.metadata.get('language')) if x.metadata.get('language') in swl else 999)
            sub_candidates = []
            if len(filtered_subtitle_streams) > 0 and not (self.settings.cleanit and cleanit):  # Don't burn embedded subtitles if we're cleaning, favor external
                first_index = sorted([x.index for x in subtitle_streams])[0]

                # Filter subtitles to be burned based on setting
                sub_candidates = [x for x in filtered_subtitle_streams if self.checkDisposition(self.settings.burn_dispositions, x.disposition)]
                # Filter out image based subtitles (until we can find a method to get this to work)
                for x in sub_candidates[:]:
                    try:
                        if self.isImageBasedSubtitle(inputfile, x.index):
                            sub_candidates.remove(x)
                    except KeyboardInterrupt:
                        raise
                    except:
                        self.log.error("Unknown error occurred while trying to determine if subtitle is text or image based. Probably corrupt, skipping.")
                        sub_candidates.remove(x)

                if len(sub_candidates) > 0:
                    self.log.debug("Found %d potential sources from the included subs for burning [burn-subtitle]." % len(sub_candidates))
                    sub_candidates = self.sortStreams(
                        sub_candidates,
                        self.settings.burn_sorting,
                        swl,
                        self.settings.sub_sorting_codecs or (self.settings.scodec + self.settings.scodec_image),
                        info,
                        tagdata=tagdata
                    )
                    burn_sub = sub_candidates[0]
                    relative_index = burn_sub.index - first_index
                    self.log.info("Burning subtitle %d %s into video steram [burn-subtitles]." % (burn_sub.index, burn_sub.metadata['language']))
                    self.log.debug("Video codec cannot be copied because valid burn subtitle was found [burn-subtitle: %s]." % (self.settings.burn_subtitles))
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
                    except KeyboardInterrupt:
                        raise
                    except:
                        self.log.error("Unknown error occurred while trying to determine if subtitle is text or image based. Probably corrupt, skipping.")
                        sub_candidates.remove(x)

                if len(sub_candidates) > 0:
                    sub_candidates = self.sortStreams(
                        sub_candidates,
                        self.settings.burn_sorting,
                        swl,
                        self.settings.sub_sorting_codecs or (self.settings.scodec + self.settings.scodec_image),
                        info
                    )
                    burn_sub = sub_candidates[0]
                    self.log.info("Burning external subtitle %s %s into video steram [burn-subtitles, embed-subs]." % (os.path.basename(burn_sub.path), burn_sub.subtitle[0].metadata['language']))
                    return "subtitles='%s'" % (self.raw(os.path.abspath(burn_sub.path)))
            self.log.info("No valid subtitle stream candidates found to be burned into video stream [burn-subtitles].")
        return None

    # Scan for external subtitle files
    def scanForExternalSubs(self, inputfile, swl, valid_external_subs=None):
        valid_external_subs = valid_external_subs or []
        input_dir, filename, _ = self.parseFile(inputfile)
        for dirName, _, fileList in os.walk(input_dir):
            for fname in fileList:
                if any(os.path.join(dirName, fname) == x.path for x in valid_external_subs):
                    self.log.debug("Already loaded %s, skipping." % (fname))
                    continue
                if fname.startswith(filename):  # filename in fname:
                    _, _, extension = self.parseFile(filename)
                    valid_external_sub = self.isValidSubtitleSource(os.path.join(dirName, fname))
                    if valid_external_sub:
                        self.log.debug("Potential subtitle candidate identified %s." % (fname))
                        valid_external_sub = self.processExternalSub(valid_external_sub, inputfile)
                        lang = valid_external_sub.subtitle[0].metadata['language']
                        default = valid_external_sub.subtitle[0].disposition['default']
                        if (self.validLanguage(lang, swl) or (self.settings.force_subtitle_defaults and default)) and valid_external_sub:
                            self.log.debug("Valid external %s subtitle file detected %s." % (lang, fname))
                            valid_external_subs.append(valid_external_sub)
                        else:
                            self.log.debug("Ignoring %s external subtitle stream due to language %s." % (fname, lang))
            break
        self.log.info("Scanned for external subtitles and found %d results in your approved languages." % (len(valid_external_subs)))
        valid_external_subs.sort(key=lambda x: swl.index(x.subtitle[0].metadata['language']) if x.subtitle[0].metadata['language'] in swl else 999)

        return valid_external_subs

    # Process external subtitle file with CleanIt library
    def cleanExternalSub(self, path):
        if self.settings.cleanit and cleanit:
            self.log.debug("Cleaning subtitle with path %s [subtitles.cleanit]." % (path))
            sub = cleanit.Subtitle(path)
            cfg = cleanit.Config.from_path(self.settings.cleanit_config) if self.settings.cleanit_config else cleanit.Config()
            rules = cfg.select_rules(tags=self.settings.cleanit_tags)
            if sub.clean(rules):
                sub.save()

    # FFSubsync
    def syncExternalSub(self, path, inputfile):
        if self.settings.ffsubsync and ffsubsync:
            self.log.debug("Syncing subtitle with path %s [subtitles.ffsubsync]." % (path))
            syncedsub = path + ".sync"
            try:
                unparsed_args = [inputfile, '-i', path, '-o', syncedsub, '--ffmpegpath', os.path.dirname(self.settings.ffmpeg)]
                parser = ffsubsync.make_parser()
                self.args = parser.parse_args(args=unparsed_args)
                if os.path.isfile(syncedsub):
                    os.remove(syncedsub)
                result = ffsubsync.run(self.args)
                self.log.debug(result)
                if os.path.exists(syncedsub):
                    os.remove(path)
                    os.rename(syncedsub, path)
            except Exception:
                self.log.exception("Exception syncing subtitle %s." % (path))

    # Custom method to allow additional video data to be passed to subliminal for better subtitle accuracy
    @staticmethod
    def custom_scan_video(path, tagdata=None):
        # check for non-existing path
        if not os.path.exists(path):
            raise ValueError('Path does not exist')

        # check video extension
        if not path.lower().endswith(subliminal.VIDEO_EXTENSIONS):
            raise ValueError('%r is not a valid video extension' % os.path.splitext(path)[1])

        options = None
        if tagdata and tagdata.mediatype == MediaType.TV:
            options = {'type': 'episode'}
        elif tagdata and tagdata.mediatype == MediaType.Movie:
            options = {'type': 'movie'}

        guess = guessit(path, options)

        if tagdata and tagdata.mediatype == MediaType.TV:
            guess['episode'] = tagdata.episode
            guess['title'] = tagdata.title
            guess['season'] = tagdata.season
        elif tagdata and tagdata.mediatype == MediaType.Movie:
            guess['title'] = tagdata.title

        video = subliminal.Video.fromguess(path, guess)

        # size
        video.size = os.path.getsize(path)

        return video

    # Download subtitles using subliminal
    def downloadSubtitles(self, inputfile, existing_subtitle_streams, swl, original=None, tagdata=None):
        if (self.settings.downloadsubs or self.settings.downloadforcedsubs) and subliminal and guessit and Language:
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
                video = MediaProcessor.custom_scan_video(os.path.abspath(inputfile), tagdata)

                if self.settings.ignore_embedded_subs:
                    video.subtitle_languages = set()
                else:
                    video.subtitle_languages = set([Language(x.metadata['language']) for x in existing_subtitle_streams])

                if tagdata:
                    self.log.debug("Refining subliminal search using included metadata")
                    tagdate = tagdata.date
                    try:
                        tagdate = tagdata.date[:4]
                    except:
                        pass
                    video.year = tagdate or video.year
                    video.imdb_id = tagdata.imdbid or video.imdb_id
                    if tagdata.mediatype == MediaType.Movie and isinstance(video, subliminal.Movie):
                        subliminal.refine(video, title=tagdata.title, year=tagdate, imdb_id=tagdata.imdbid)
                        video.title = tagdata.title or video.title
                    elif tagdata.mediatype == MediaType.TV and isinstance(video, subliminal.Episode):
                        subliminal.refine(video, series=tagdata.showname, year=tagdate, series_imdb_id=tagdata.imdbid, series_tvdb_id=tagdata.tvdbid, title=tagdata.title)
                        video.series_tvdb_id = tagdata.tvdbid or video.series_tvdb_id
                        video.series_imdb_id = tagdata.imdbid or video.series_imdb_id
                        video.season = tagdata.season or video.season
                        video.episodes = [tagdata.episode] or video.episodes
                        video.series = tagdata.showname or video.series
                        video.title = tagdata.title or video.title

                # If data about the original release is available, include that in the search to best chance at accurate subtitles
                if original:
                    try:
                        self.log.debug("Found original filename, adding data from %s." % original)
                        og = guessit(original)
                        self.log.debug("Source %s, release group %s, resolution %s, streaming service %s." % (og.get('source'), og.get('release_group'), og.get('screen_size'), og.get('streaming_service')))
                        video.source = og.get('source') or video.source
                        video.release_group = og.get('release_group') or video.release_group
                        video.resolution = og.get('screen_size') or video.resolution
                        video.streaming_service = og.get('streaming_service') or video.streaming_service
                    except KeyboardInterrupt:
                        raise
                    except:
                        self.log.exception("Error importing original file data for subliminal, will attempt to proceed.")

                paths = []
                if self.settings.downloadforcedsubs:
                    forced_subtitles = [s for s in subliminal.list_subtitles([video], languages, providers=self.settings.subproviders, provider_configs=self.settings.subproviders_auth)[video] if ".forced" in s.info.lower()]
                    self.log.debug("Found %d potential forced subtitles." % (len(forced_subtitles)))
                    subliminal.download_subtitles(forced_subtitles, providers=self.settings.subproviders, provider_configs=self.settings.subproviders_auth)
                    saves = subliminal.save_subtitles(video, forced_subtitles)
                    paths.extend([(subliminal.subtitle.get_subtitle_path(video.name, x.language), x) for x in saves])
                    for path, sub in paths:
                        if ".forced" in sub.info and ".forced" not in path:
                            base, ext = os.path.splitext(path)
                            os.rename(path, "%s.forced%s" % (base, ext))
                if self.settings.downloadsubs:
                    subtitles = subliminal.download_best_subtitles([video], languages, hearing_impaired=self.settings.hearing_impaired, providers=self.settings.subproviders, provider_configs=self.settings.subproviders_auth)
                    saves = subliminal.save_subtitles(video, subtitles[video])
                    paths.extend([(subliminal.subtitle.get_subtitle_path(video.name, x.language), x) for x in saves])
                for path, sub in paths:
                    self.log.info("Downloaded new subtitle %s from source %s." % (path, sub.info))
                    self.setPermissions(path)
                return [p for p, _ in paths]
            except KeyboardInterrupt:
                raise
            except:
                self.log.exception("Unable to download subtitles.")
        return []

    # Scan for external chapters file
    def scanForExternalMetadata(self, inputfile, suffix="metadata.txt"):
        input_dir, filename, _ = self.parseFile(inputfile)
        for dirName, _, fileList in os.walk(input_dir):
            for fname in fileList:
                if fname.startswith(filename) and fname.endswith(suffix):
                    self.log.debug("Found valid external metadata file %s." % (fname))
                    return os.path.join(dirName, fname)
        return None

    # Generic permission setter
    def setPermissions(self, path):
        try:
            if os.path.exists(path):
                os.chmod(path, self.settings.permissions.get('chmod', int('0664', 8)))
                if os.name != 'nt':
                    os.chown(path, self.settings.permissions.get('uid', -1), self.settings.permissions.get('gid', -1))
            else:
                self.log.debug("File %s does not exist, unable to set permissions." % path)
        except:
            self.log.exception("Unable to set new file permissions.")

    # Undo output dir
    def restoreFromOutput(self, inputfile, outputfile):
        if self.settings.output_dir and not self.settings.moveto and os.path.commonpath([self.settings.output_dir, outputfile]) == self.settings.output_dir:
            input_dir, _, _ = self.parseFile(inputfile)
            outputfilename = os.path.split(outputfile)[1]
            try:
                newoutputfile = os.path.join(input_dir.decode(sys.getfilesystemencoding()), outputfilename.decode(sys.getfilesystemencoding()))
            except:
                newoutputfile = os.path.join(input_dir, outputfilename)
            self.log.info("Output file is in output_dir %s, moving back to original directory %s." % (self.settings.output_dir, input_dir))
            self.log.debug("New outputfile %s." % (newoutputfile))
            try:
                shutil.move(outputfile, newoutputfile)
            except KeyboardInterrupt:
                raise
            except:
                self.log.exception("First attempt to move the file has failed.")
                try:
                    if os.path.exists(newoutputfile):
                        self.removeFile(newoutputfile, 0, 0)
                    shutil.move(outputfile, newoutputfile)
                except KeyboardInterrupt:
                    raise
                except:
                    self.log.exception("Unable to move %s to %s" % (outputfile, newoutputfile))
                    return outputfile
            return newoutputfile
        return outputfile

    # Reverse map option back to source stream
    def getSourceStream(self, index, info):
        return info.streams[index]

    # Safely get codec from options
    def getCodecFromOptions(self, x, info):
        return self.getSourceStream(x['map'], info).codec if x.get('codec') == 'copy' else x.get('codec')

    # Get subtitle extension based on codec
    def getSubExtensionFromCodec(self, codec):
        try:
            return subtitle_codec_extensions[codec]
        except:
            self.log.info("Wasn't able to determine subtitle file extension, defaulting to codec %s." % codec)
            return codec

    # Get subtitle file name based on options
    def getSubOutputFileFromOptions(self, inputfile, options, extension):
        language = options["language"]
        return self.getSubOutputFile(inputfile, language, options['disposition'], extension)

    # Get subtitle file name based on language, disposition, and extension
    def getSubOutputFile(self, inputfile, language, disposition, extension):
        disposition = self.dispoStringToDict(disposition)
        dispo = ""
        for k in disposition:
            if disposition[k] and k in self.settings.filename_dispositions:
                dispo += "." + k
        input_dir, filename, input_extension = self.parseFile(inputfile)
        output_dir = self.settings.output_dir or input_dir
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except:
                self.log.exception("Unable to make output directory %s." % (output_dir))
        outputfile = os.path.join(output_dir, filename + "." + language + dispo + "." + extension)

        i = 2
        while os.path.isfile(outputfile):
            self.log.debug("%s exists, appending %s to filename." % (outputfile, i))
            outputfile = os.path.join(output_dir, filename + "." + language + dispo + "." + str(i) + "." + extension)
            i += 1
        return outputfile

    # Generate options to rip a subtitle from a container file
    def generateRipSubOpts(self, inputfile, s, scodec):
        ripsub = [{
            'map': s.index,
            'codec': scodec,
            'language': s.metadata['language'],
            'debug': "subtitle"
        }]
        options = {
            'source': [inputfile],
            'subtitle': ripsub,
            'format': s.codec if scodec == 'copy' else scodec,
            'disposition': s.dispostr,
            'language': s.metadata['language'],
            'index': s.index
        }
        return options

    # Rip subtitle from container
    def ripSubs(self, inputfile, ripsubopts):
        rips = []
        ripsubopts = ripsubopts if isinstance(ripsubopts, list) else [ripsubopts]
        for options in ripsubopts:
            extension = self.getSubExtensionFromCodec(options['format'])
            outputfile = self.getSubOutputFileFromOptions(inputfile, options, extension)

            try:
                self.log.info("Ripping %s subtitle from source stream %s into external file." % (options["language"], options['index']))
                conv = self.converter.convert(outputfile, options, timeout=None)
                _, cmds = next(conv)
                self.log.debug("Subtitle extraction FFmpeg command:")
                self.log.debug(self.printableFFMPEGCommand(cmds))
                for _, debug in conv:
                    self.log.debug(debug)
                self.log.info("%s created." % outputfile)
                rips.append(outputfile)
            except (FFMpegConvertError, ConverterError):
                self.log.error("Unable to create external %s subtitle file for stream %s, may be an incompatible format." % (extension, options['index']))
                self.removeFile(outputfile)
                continue
            except KeyboardInterrupt:
                raise
            except:
                self.log.exception("Unable to create external subtitle file for stream %s." % (options['index']))
            self.setPermissions(outputfile)
        return rips

    # Get output file name
    def getOutputFile(self, input_dir, filename, input_extension, temp_extension=None, ignore_output_dir=False, number=0):
        if ignore_output_dir:
            output_dir = input_dir
        else:
            output_dir = self.settings.output_dir or input_dir
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except:
                self.log.exception("Unable to make output directory %s." % (output_dir))
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

    # Framedata normalization
    def parseAndNormalize(self, inputstring, denominator, splitter="/"):
        n, d = [float(x) for x in inputstring.split(splitter)]
        if d == denominator:
            return n
        return int(round((n / d) * denominator))

    # Ensure framedata has minimum parameters
    def hasValidFrameData(self, framedata):
        try:
            if 'side_data_list' in framedata:
                types = [x['side_data_type'] for x in framedata['side_data_list'] if 'side_data_type' in x]
                if 'Mastering display metadata' in types and 'Content light level metadata' in types:
                    return True
            return False
        except:
            return False

    def hasBitstreamVideoSubs(self, framedata):
        if 'side_data_list' in framedata:
            for side_data in framedata['side_data_list']:
                if "closed captions" in side_data.get('side_data_type', '').lower():
                    return True
        return False

    # Framedata normalization
    def normalizeFramedata(self, framedata, hdr):
        try:
            if hdr:
                framedata['hdr'] = True
                framedata['repeat-headers'] = True
            if 'side_data_list' in framedata:
                for side_data in framedata['side_data_list']:
                    if side_data.get('side_data_type') == 'Mastering display metadata':
                        side_data['red_x'] = self.parseAndNormalize(side_data.get('red_x'), 50000)
                        side_data['red_y'] = self.parseAndNormalize(side_data.get('red_y'), 50000)
                        side_data['green_x'] = self.parseAndNormalize(side_data.get('green_x'), 50000)
                        side_data['green_y'] = self.parseAndNormalize(side_data.get('green_y'), 50000)
                        side_data['blue_x'] = self.parseAndNormalize(side_data.get('blue_x'), 50000)
                        side_data['blue_y'] = self.parseAndNormalize(side_data.get('blue_y'), 50000)
                        side_data['white_point_x'] = self.parseAndNormalize(side_data.get('white_point_x'), 50000)
                        side_data['white_point_y'] = self.parseAndNormalize(side_data.get('white_point_y'), 50000)
                        side_data['min_luminance'] = self.parseAndNormalize(side_data.get('min_luminance'), 10000)
                        side_data['max_luminance'] = self.parseAndNormalize(side_data.get('max_luminance'), 10000)
                        break
            return framedata
        except:
            return framedata

    def isDolbyVision(self, framedata):
        try:
            if 'side_data_list' in framedata:
                for side_data in framedata['side_data_list']:
                    if side_data.get('side_data_type', '').lower() == "dolby vision metadata":
                        return True
        except:
            return False
        return False

    # Check if video stream meets criteria to be considered HDR
    def isHDR(self, videostream):
        if len(self.settings.hdr['space']) < 1 and len(self.settings.hdr['transfer']) < 1 and len(self.settings.hdr['primaries']) < 1:
            self.log.debug("No HDR screening parameters defined, returning false [hdr].")
            return False

        params = ['space', 'transfer', 'primaries']
        for param in params:
            if param in videostream.color and len(self.settings.hdr.get(param)) > 0 and videostream.color.get(param) not in self.settings.hdr.get(param):
                self.log.debug("Stream is not HDR, color parameter %s does not match %s [hdr-%s]." % (videostream.color.get(param), self.settings.hdr.get(param), self.settings.hdr.get(param)))
                return False

        self.log.info("HDR video stream detected for %d." % videostream.index)
        return True

    # Run test conversion of subtitle to see if its image based, does not appear to be any other way to tell dynamically
    def isImageBasedSubtitle(self, inputfile, map):
        ripsub = [{'map': map, 'codec': 'srt'}]
        options = {'source': [inputfile], 'format': 'srt', 'subtitle': ripsub}
        postopts = ['-t', '00:00:01']
        try:
            conv = self.converter.convert(None, options, timeout=30, postopts=postopts)
            _, cmds = next(conv)
            self.log.debug("isImageBasedSubtitle FFmpeg command:")
            self.log.debug(self.printableFFMPEGCommand(cmds))
            for _, debug in conv:
                if debug:
                    self.log.debug(debug)
        except FFMpegConvertError:
            return True
        return False

    # Check if video file meets criteria to just bypass conversion
    def canBypassConvert(self, inputfile, info, options=None):
        # Process same extensions
        if self.settings.output_extension == self.parseFile(inputfile)[2]:
            if not self.settings.force_convert and not self.settings.process_same_extensions:
                self.log.info("Input and output extensions are the same so passing back the original file [process-same-extensions: %s]." % self.settings.process_same_extensions)
                return True
            elif info.format.metadata.get('encoder', '').startswith('sma') and not self.settings.force_convert:
                self.log.info("Input and output extensions match and the file appears to have already been processed by SMA, enable force-convert to override [force-convert: %s]." % self.settings.force_convert)
                return True
            elif self.settings.bypass_copy_all and options and len([x for x in [options['video']] + [x for x in options['audio']] + [x for x in options['subtitle']] if x['codec'] != 'copy']) == 0 and len(options['audio']) == len(info.audio) and len(options['subtitle']) == len(info.subtitle) and not self.settings.force_convert:
                self.log.info("Input and output extensions match, the file appears to copying all streams, and is not reducing the number of streams, enable force-convert to override [bypass-if-copying-all] [force-convert: %s]." % self.settings.force_convert)
                return True
        self.log.debug("canBypassConvert returned False.")
        return False

    # Generate copy/paste friendly FFMPEG command
    def printableFFMPEGCommand(self, cmds):
        return " ".join("\"%s\"" % item if (" " in item or "|" in item) and "\"" not in item else item for item in cmds)

    # Encode a new file based on selected options, built in naming conflict resolution
    def convert(self, options, preopts, postopts, reportProgress=False, progressOutput=None):
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
                        if self.raw(os.path.abspath(inputfile)) in (options['video'].get('filter') or ""):
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
            conv = self.converter.convert(outputfile, options, timeout=None, preopts=preopts, postopts=postopts, strip_metadata=self.settings.strip_metadata)
        except KeyboardInterrupt:
            raise
        except:
            self.log.exception("Error converting file.")
            return None, inputfile

        _, cmds = next(conv)
        self.log.info("FFmpeg command:")
        self.log.info("======================")
        self.log.info(self.printableFFMPEGCommand(cmds))
        self.log.info("======================")

        try:
            timecode = 0
            debug = ""
            for timecode, debug in conv:
                if reportProgress:
                    if progressOutput:
                        progressOutput(timecode, debug)
                    else:
                        self.displayProgressBar(timecode, debug)
            if reportProgress:
                if progressOutput:
                    progressOutput(100, debug)
                else:
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
            except KeyboardInterrupt:
                raise
            except:
                self.log.exception("Error restoring original inputfile after exception.")
                return None, inputfile
        except KeyboardInterrupt:
            raise
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
            except KeyboardInterrupt:
                raise
            except:
                self.log.exception("Unable to rename output file to its final destination file extension [temp_extension].")
                finaloutputfile = outputfile

        return finaloutputfile, inputfile

    # Generate progress bar
    def displayProgressBar(self, complete, debug="", width=20, newline=False):
        try:
            divider = 100 / width

            if complete > 100:
                complete = 100

            sys.stdout.write('\r')
            sys.stdout.write('[{0}] {1}% '.format('#' * int(round(complete / divider)) + ' ' * int(round(width - (complete / divider))), complete))
            if debug and self.settings.detailedprogress:
                if complete == 100:
                    sys.stdout.write("%s" % debug.strip())
                else:
                    sys.stdout.write(" %s" % debug.strip())
            if newline:
                sys.stdout.write('\n')
            sys.stdout.flush()
        except KeyboardInterrupt:
            raise
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
        TEMP_EXT = '.QTFS'
        # Relocate MOOV atom to the very beginning. Can double the time it takes to convert a file but makes streaming faster
        if os.path.isfile(inputfile) and self.settings.relocate_moov and self.settings.output_format not in ['mkv']:
            from qtfaststart import processor, exceptions

            self.log.info("Relocating MOOV atom to start of file.")

            try:
                outputfile = inputfile.decode(sys.getfilesystemencoding()) + TEMP_EXT
            except:
                outputfile = inputfile + TEMP_EXT

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
                self.log.debug("QT FastStart did not run - perhaps moov atom was at the start already or file is in the wrong format.")
                return inputfile
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
                except KeyboardInterrupt:
                    raise
                except:
                    self.log.exception("First attempt to copy the file has failed.")
                    try:
                        if os.path.exists(os.path.join(d, os.path.split(inputfile)[1])):
                            self.removeFile(os.path.join(d, os.path.split(inputfile)[1]), 0, 0)
                        try:
                            shutil.copy(inputfile.decode(sys.getfilesystemencoding()), d)
                        except KeyboardInterrupt:
                            raise
                        except:
                            shutil.copy(inputfile, d)
                        self.log.info("%s copied to %s." % (inputfile, d))
                        files.append(os.path.join(d, os.path.split(inputfile)[1]))
                    except KeyboardInterrupt:
                        raise
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
            except KeyboardInterrupt:
                raise
            except:
                self.log.exception("First attempt to move the file has failed.")
                try:
                    if os.path.exists(os.path.join(moveto, os.path.basename(inputfile))):
                        self.removeFile(os.path.join(moveto, os.path.basename(inputfile)), 0, 0)
                    shutil.move(inputfile.decode(sys.getfilesystemencoding()), moveto)
                    self.log.info("%s moved to %s." % (inputfile, moveto))
                    files[0] = os.path.join(moveto, os.path.basename(inputfile))
                except KeyboardInterrupt:
                    raise
                except:
                    self.log.exception("Unable to move %s to %s" % (inputfile, moveto))
        for filename in files:
            self.log.debug("Final output file: %s." % filename)
        return files

    def outputDirHasFreeSpace(self, inputfile):
        if self.settings.output_dir and self.settings.output_dir_ratio:
            try:
                needed = os.path.getsize(inputfile) * self.settings.output_dir_ratio
                usage = shutil.disk_usage(self.settings.output_dir)
                enough = usage.free > needed
                if not enough:
                    self.log.info("Output-directory does not have enough free space (%s needed) [output-directory-space-ratio]." % needed)
                return enough
            except:
                self.log.exception("Unable to check free space on output directory %s [output-directory-space-ratio]." % self.settings.output_dir)
        return True

    # Robust file removal function, with options to retry in the event the file is in use, and replace a deleted file
    def removeFile(self, filename, retries=2, delay=10, replacement=None):
        for _ in range(retries + 1):
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
            except KeyboardInterrupt:
                raise
            except:
                self.log.exception("Unable to remove or replace file %s." % filename)
                if delay > 0:
                    self.log.debug("Delaying for %s seconds before retrying." % delay)
                    time.sleep(delay)
        return False if os.path.isfile(filename) else True

    # Formatter needed for burn subtitle filter syntax
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
