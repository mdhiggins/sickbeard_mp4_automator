#!/usr/bin/env python3

import sys
import os
import guessit
import locale
import glob
import argparse
import struct
import enum
import json
import logging
import tmdbsimple as tmdb
from resources.log import getLogger
from resources.readsettings import ReadSettings
from resources.mediaprocessor import MediaProcessor
from resources.metadata import Metadata, MediaType
from resources.postprocess import PostProcessor
from resources.extensions import tmdb_api_key
from converter.avcodecs import audio_codec_list, video_codec_list, subtitle_codec_list, attachment_codec_list

if sys.version[0] == "3":
    raw_input = input

os.environ["REGEX_DISABLED"] = "1"  # Fixes Toilal/rebulk#20

log = getLogger("MANUAL")

logging.getLogger("subliminal").setLevel(logging.CRITICAL)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("enzyme").setLevel(logging.WARNING)
logging.getLogger("qtfaststart").setLevel(logging.CRITICAL)
logging.getLogger("rebulk").setLevel(logging.WARNING)

log.info("Manual processor started.")


class MediaTypes(enum.Enum):
    @classmethod
    def descriptors(cls):
        return {
            cls.MOVIE_TMDB: "Movie (via TMDB)",
            cls.MOVIE_IMDB: "Movie (via IMDB)",
            cls.TV_TMDB: "TV (via TMDB)",
            cls.TV_TVDB: "TV (via TVDB)",
            cls.TV_IMDB: "TV (via IMDB)",
            cls.CONVERT: "Convert without tagging",
            cls.SKIP: "Skip file"
        }

    def __str__(self):
        return "{0}. {1}".format(self.value, MediaTypes.descriptors().get(self, ""))

    MOVIE_TMDB = 1
    MOVIE_IMDB = 2
    TV_TMDB = 3
    TV_TVDB = 4
    TV_IMDB = 5
    CONVERT = 6
    SKIP = 7


def mediatype():
    try:
        print("Select media type:")
        for mt in MediaTypes:
            print(str(mt))
        result = raw_input("#: ")
        try:
            return MediaTypes(int(result))
        except KeyboardInterrupt:
            raise
        except:
            print("Invalid selection")
            return mediatype()
    except EOFError:
        print("Invalid selection")
        return mediatype()


def getValue(prompt, num=False):
    try:
        print(prompt + ":")
        value = raw_input("#: ").strip(' \"')
        # Remove escape characters in non-windows environments
        if os.name != 'nt':
            value = value.replace('\\', '')
        try:
            value = value.decode(sys.stdout.encoding)
        except:
            pass
        if num is True and value.isdigit() is False:
            print("Must be a numerical value")
            return getValue(prompt, num)
        else:
            return value
    except EOFError:
        print("Must be a numerical value")
        return getValue(prompt, num)


def getYesNo():
    yes = ['y', 'yes', 'true', '1']
    no = ['n', 'no', 'false', '0']
    try:
        data = raw_input("# [y/n]: ")
        if data.lower() in yes:
            return True
        elif data.lower() in no:
            return False
        else:
            print("Invalid selection")
            return getYesNo()
    except EOFError:
        print("Invalid selection")
        return getYesNo()


class SkipFileException(Exception):
    pass


def getInfo(fileName, settings, silent=False, tag=True, tvdbid=None, tmdbid=None, imdbid=None, season=None, episode=None, language=None, original=None):
    if not tag:
        return None

    tagdata = None
    # Try to guess the file is guessing is enabled
    if fileName is not None:
        tagdata = guessInfo(fileName, settings, tvdbid=tvdbid, tmdbid=tmdbid, imdbid=imdbid, season=season, episode=episode, language=language, original=original)

    if not silent:
        if tagdata:
            print("Proceed using guessed identification from filename?")
            if getYesNo():
                return tagdata
        else:
            print("Unable to determine identity based on filename, must enter manually")
        m_type = mediatype()
        if m_type is MediaTypes.TV_TMDB:
            tmdbid = getValue("Enter TMDB ID (TV)", True)
            season = getValue("Enter Season Number", True)
            episode = getValue("Enter Episode Number", True)
            return Metadata(MediaType.TV, tmdbid=tmdbid, season=season, episode=episode, language=language, logger=log, original=original)
        if m_type is MediaTypes.TV_TVDB:
            tvdbid = getValue("Enter TVDB ID (TV)", True)
            season = getValue("Enter Season Number", True)
            episode = getValue("Enter Episode Number", True)
            return Metadata(MediaType.TV, tvdbid=tvdbid, season=season, episode=episode, language=language, logger=log, original=original)
        if m_type is MediaTypes.TV_IMDB:
            imdbid = getValue("Enter IMDB ID (TV)", True)
            season = getValue("Enter Season Number", True)
            episode = getValue("Enter Episode Number", True)
            return Metadata(MediaType.TV, imdbid=imdbid, season=season, episode=episode, language=language, logger=log, original=original)
        elif m_type is MediaTypes.MOVIE_IMDB:
            imdbid = getValue("Enter IMDB ID (Movie)")
            return Metadata(MediaType.Movie, imdbid=imdbid, language=language, logger=log, original=original)
        elif m_type is MediaTypes.MOVIE_TMDB:
            tmdbid = getValue("Enter TMDB ID (Movie)", True)
            return Metadata(MediaType.Movie, tmdbid=tmdbid, language=language, logger=log, original=original)
        elif m_type is MediaTypes.CONVERT:
            return None
        elif m_type is MediaTypes.SKIP:
            raise SkipFileException
    else:
        if tagdata and tag:
            return tagdata
        else:
            return None


def guessInfo(fileName, settings, tmdbid=None, tvdbid=None, imdbid=None, season=None, episode=None, language=None, original=None):
    if not settings.fullpathguess:
        fileName = os.path.basename(fileName)
    guess = guessit.guessit(original or fileName)
    try:
        if guess['type'] == 'movie':
            return movieInfo(guess, tmdbid=tmdbid, imdbid=imdbid, language=language, original=original)
        elif guess['type'] == 'episode':
            return tvInfo(guess, tmdbid=tmdbid, tvdbid=tvdbid, imdbid=imdbid, season=season, episode=episode, language=language, original=original)
        else:
            return None
    except KeyboardInterrupt:
        raise
    except:
        log.exception("Unable to guess movie information")
        return None


def movieInfo(guessData, tmdbid=None, imdbid=None, language=None, original=None):
    if not tmdbid and not imdbid:
        tmdb.API_KEY = tmdb_api_key
        search = tmdb.Search()
        title = guessData['title']
        if 'year' in guessData:
            _ = search.movie(query=title, year=guessData["year"])
            if len(search.results) < 1:
                _ = search.movie(query=title, year=guessData["year"])
        else:
            _ = search.movie(query=title)
        if len(search.results) < 1:
            return None
        result = search.results[0]
        # release = result['release_date']
        tmdbid = result['id']
        log.debug("Guessed filename resulted in TMDB ID %s" % tmdbid)

    metadata = Metadata(MediaType.Movie, tmdbid=tmdbid, imdbid=imdbid, language=language, logger=log, original=original)
    log.info("Matched movie title as: %s %s (TMDB ID: %s)" % (metadata.title, metadata.date, metadata.tmdbid))
    return metadata


def tvInfo(guessData, tmdbid=None, tvdbid=None, imdbid=None, season=None, episode=None, language=None, original=None):
    season = season or guessData.get("season", 0)
    episode = episode or guessData.get("episode", 0)
    if type(episode) == list:
        episode = episode[0]

    if not tmdbid and not tvdbid and not imdbid:
        tmdb.API_KEY = tmdb_api_key
        search = tmdb.Search()
        series = guessData["title"]
        if 'year' in guessData:
            _ = search.tv(query=series, first_air_date_year=guessData["year"])
            if len(search.results) < 1:
                _ = search.tv(query=series)
        else:
            _ = search.tv(query=series)
        if search and len(search.results) < 1:
            return None
        result = search.results[0]
        tmdbid = result['id']

    metadata = Metadata(MediaType.TV, tmdbid=tmdbid, imdbid=imdbid, tvdbid=tvdbid, season=season, episode=episode, language=language, logger=log, original=original)
    log.info("Matched TV episode as %s (TMDB ID: %d) S%02dE%02d" % (metadata.showname, int(metadata.tmdbid), int(season), int(episode)))
    return metadata


def checkAlreadyProcessed(inputfile, processedList):
    if processedList is None:
        return False

    return inputfile in processedList


def addtoProcessedArchive(files, processedList, processedArchive):
    if processedList is None or processedArchive is None:
        return

    processedList.extend(files)
    with open(processedArchive, 'w', encoding="utf8") as pa:
        json.dump(list(set(processedList)), pa, indent=4)
    log.debug("Adding %s to processed archive %s" % (files, processedArchive))


def processFile(inputfile, mp, info=None, relativePath=None, silent=False, tag=True, tagonly=False, tmdbid=None, tvdbid=None, imdbid=None, season=None, episode=None, original=None, processedList=None, processedArchive=None):
    if checkAlreadyProcessed(inputfile, processedList):
        log.debug("%s is already processed and will be skipped based on archive %s." % (inputfile, processedArchive))
        return

    # Process
    info = info or mp.isValidSource(inputfile)
    if not info:
        log.debug("Invalid file %s." % inputfile)
        return

    language = mp.settings.taglanguage or None
    tagdata = getInfo(inputfile, mp.settings, silent=silent, tag=tag or tagonly, tmdbid=tmdbid, tvdbid=tvdbid, imdbid=imdbid, season=season, episode=episode, language=language, original=original)

    if not tagdata:
        log.info("Processing file %s" % inputfile)
    elif tagdata.mediatype == MediaType.Movie:
        log.info("Processing %s" % (tagdata.title))
    elif tagdata.mediatype == MediaType.TV:
        log.info("Processing %s Season %02d Episode %02d - %s" % (tagdata.showname, int(tagdata.season), int(tagdata.episode), tagdata.title))

    if tagonly:
        if tagdata:
            try:
                tagdata.writeTags(inputfile, inputfile, mp.converter, mp.settings.artwork, mp.settings.thumbnail)
                if mp.settings.relocate_moov:
                    mp.QTFS(inputfile)
            except KeyboardInterrupt:
                raise
            except:
                log.exception("There was an error tagging the file")
        return

    output = mp.process(inputfile, True, info=info, original=original, tagdata=tagdata)
    if output:
        if not language:
            language = mp.getDefaultAudioLanguage(output["options"]) or None
            if language and tagdata:
                tagdata = Metadata(tagdata.mediatype, tmdbid=tagdata.tmdbid, imdbid=tagdata.imdbid, tvdbid=tagdata.tvdbid, season=tagdata.season, episode=tagdata.episode, original=original, language=language, logger=log)
        log.debug("Tag language setting is %s, using language %s for tagging." % (mp.settings.taglanguage or None, language))
        tagfailed = False
        if tagdata:
            try:
                tagdata.writeTags(output['output'], inputfile, mp.converter, mp.settings.artwork, mp.settings.thumbnail, width=output['x'], height=output['y'], streaming=output['rsi'])
            except KeyboardInterrupt:
                raise
            except:
                log.exception("There was an error tagging the file")
                tagfailed = True
        if mp.settings.relocate_moov and not tagfailed:
            mp.QTFS(output['output'])

        # Reverse Ouput
        output['output'] = mp.restoreFromOutput(inputfile, output['output'])

        output_files = mp.replicate(output['output'], relativePath=relativePath)
        print(json.dumps(output, indent=4))
        for sub in [x for x in output['external_subs'] if os.path.exists(x)]:
            output_files.extend(mp.replicate(sub, relativePath=relativePath))
        for file in output_files:
            mp.setPermissions(file)
        if mp.settings.postprocess:
            postprocessor = PostProcessor(output_files, wait=mp.settings.waitpostprocess)
            if tagdata:
                if tagdata.mediatype == MediaType.Movie:
                    postprocessor.setMovie(tagdata.tmdbid)
                elif tagdata.mediatype == MediaType.TV:
                    postprocessor.setTV(tagdata.tmdbid, tagdata.season, tagdata.episode)
            postprocessor.run_scripts()
        addtoProcessedArchive(output_files + [output['input']] if not output['input_deleted'] else output_files, processedList, processedArchive)
    else:
        log.error("There was an error processing file %s, no output data received" % inputfile)


def walkDir(dir, settings, silent=False, preserveRelative=False, tmdbid=None, imdbid=None, tvdbid=None, tag=True, tagonly=False, optionsOnly=False, processedList=None, processedArchive=None):
    files = []
    error = []
    mp = MediaProcessor(settings, logger=log)
    for r, d, f in os.walk(dir):
        for file in f:
            files.append(os.path.join(r, file))
    for filepath in files:
        info = mp.isValidSource(filepath)
        if info:
            log.info("Processing file %s" % (filepath))
            relative = os.path.split(os.path.relpath(filepath, dir))[0] if preserveRelative else None
            if optionsOnly:
                displayOptions(filepath, settings)
                continue
            try:
                processFile(filepath, mp, info=info, relativePath=relative, silent=silent, tag=tag, tagonly=tagonly, tmdbid=tmdbid, tvdbid=tvdbid, imdbid=imdbid, processedList=processedList, processedArchive=processedArchive)
            except SkipFileException:
                log.debug("Skipping file %s." % filepath)
            except KeyboardInterrupt:
                break
            except:
                log.exception("Error processing file %s." % filepath)
                error.append(filepath)
    if error:
        log.error("Script failed to process the following files:")
        for e in error:
            log.error(e)


def displayOptions(path, settings):
    mp = MediaProcessor(settings)
    log.info(mp.jsonDump(path))


def showCodecs():
    data = {
        'video': video_codec_list,
        'audio': audio_codec_list,
        'subtitle': subtitle_codec_list,
        'attachment': attachment_codec_list
    }
    print("List of supported codecs within SMA")
    print("Format:")
    print("  [SMA Codec]: [FFMPEG Encoder]")
    for key in data:
        print("=============")
        print(" " + key)
        print("=============")
        for codec in data[key]:
            print("%s: %s" % (codec.codec_name, codec.ffmpeg_codec_name))


def main():
    parser = argparse.ArgumentParser(description="Manual conversion and tagging script for sickbeard_mp4_automator")
    parser.add_argument('-i', '--input', help='The source that will be converted. May be a file or a directory')
    parser.add_argument('-c', '--config', help='Specify an alternate configuration file location')
    parser.add_argument('-a', '--auto', action="store_true", help="Enable auto mode, the script will not prompt you for any further input, good for batch files. It will guess the metadata using guessit")
    parser.add_argument('-s', '--season', help="Specifiy the season number")
    parser.add_argument('-e', '--episode', help="Specify the episode number")
    parser.add_argument('-tvdb', '--tvdbid', help="Specify the TVDB ID for media")
    parser.add_argument('-imdb', '--imdbid', help="Specify the IMDB ID for media")
    parser.add_argument('-tmdb', '--tmdbid', help="Specify the TMDB ID for media")
    parser.add_argument('-nm', '--nomove', action='store_true', help="Overrides and disables the custom moving of file options that come from output_dir and move-to")
    parser.add_argument('-nc', '--nocopy', action='store_true', help="Overrides and disables the custom copying of file options that come from output_dir and move-to")
    parser.add_argument('-nd', '--nodelete', action='store_true', help="Overrides and disables deleting of original files")
    parser.add_argument('-nt', '--notag', action="store_true", help="Overrides and disables tagging when using the automated option")
    parser.add_argument('-to', '--tagonly', action="store_true", help="Only tag without conversion")
    parser.add_argument('-np', '--nopost', action="store_true", help="Overrides and disables the execution of additional post processing scripts")
    parser.add_argument('-pr', '--preserverelative', action='store_true', help="Preserves relative directories when processing multiple files using the copy-to or move-to functionality")
    parser.add_argument('-pse', '--processsameextensions', action='store_true', help="Overrides process-same-extensions setting in autoProcess.ini enabling the reprocessing of files")
    parser.add_argument('-fc', '--forceconvert', action='store_true', help="Overrides force-convert setting in autoProcess.ini and also enables process-same-extenions if true forcing the conversion of files")
    parser.add_argument('-m', '--moveto', help="Override move-to value setting in autoProcess.ini changing the final destination of the file")
    parser.add_argument('-oo', '--optionsonly', action="store_true", help="Display generated conversion options only, do not perform conversion")
    parser.add_argument('-cl', '--codeclist', action="store_true", help="Print a list of supported codecs and their paired FFMPEG encoders")
    parser.add_argument('-o', '--original', help="Specify the original source/release filename")
    parser.add_argument('-pa', '--processedarchive', help="Specify a processed list/archive so already processed files are skipped", nargs='?', const="archive.json")

    args = vars(parser.parse_args())

    # Setup the silent mode
    silent = args['auto']

    log.info("Python %s-bit %s." % (struct.calcsize("P") * 8, sys.version))
    log.info("Guessit version: %s." % guessit.__version__)

    if args['codeclist']:
        showCodecs()
        return

    # Settings overrides
    if args['config'] and os.path.exists(args['config']):
        settings = ReadSettings(args['config'], logger=log)
    elif args['config'] and os.path.exists(os.path.join(os.path.dirname(sys.argv[0]), args['config'])):
        settings = ReadSettings(os.path.join(os.path.dirname(sys.argv[0]), args['config']), logger=log)
    else:
        settings = ReadSettings(logger=log)

    processedArchive = None
    processedList = None
    if args['processedarchive'] and os.path.exists(args['processedarchive']):
        processedArchive = args['processedarchive']
        log.info("Processed archived specified at %s" % (processedArchive))
    elif args['processedarchive'] and os.path.exists(os.path.join(os.path.dirname(sys.argv[0]), args['processedarchive'])):
        processedArchive = os.path.join(os.path.dirname(sys.argv[0]), args['processedarchive'])
        log.info("Processed archived specified at %s" % (processedArchive))
    elif args['processedarchive']:
        processedArchive = os.path.normpath(args['processedarchive'])
        with open(processedArchive, 'w', encoding="utf8") as pa:
            json.dump([], pa)
        log.info("Processed archived specified at %s but file does not exist, creating" % (processedArchive))
    if processedArchive:
        pa = open(processedArchive, encoding="utf8")
        processedList = json.load(pa)
        log.info("Loaded archive list containing %d files" % (len(processedList)))

    if (args['nomove']):
        settings.output_dir = None
        settings.moveto = None
        log.info("No-move enabled")
    elif (args['moveto']):
        settings.moveto = args['moveto']
        log.info("Overriden move-to to " + args['moveto'])
    if (args['nocopy']):
        settings.copyto = None
        log.info("No-copy enabled")
    if (args['nodelete']):
        settings.delete = False
        log.info("No-delete enabled")
    if (args['processsameextensions']):
        settings.process_same_extensions = True
        log.info("Reprocessing of same extensions enabled")
    if (args['forceconvert']):
        settings.process_same_extensions = True
        settings.force_convert = True
        log.info("Force conversion of files enabled. As a result conversion of mp4 files is also enabled")
    if (args['tagonly']):
        log.info("Tag only enabled")
    elif (args['notag']):
        settings.tagfile = False
        log.info("No-tagging enabled")
    if (args['nopost']):
        settings.postprocess = False
        log.info("No post processing enabled")
    if (args['optionsonly']):
        logging.getLogger("resources.mediaprocessor").setLevel(logging.CRITICAL)
        log.info("Options only mode enabled")

    # Establish the path we will be working with
    if (args['input']):
        path = (str(args['input']))
        try:
            path = glob.glob(path)[0]
        except:
            pass
    else:
        path = getValue("Enter path to file")

    if os.path.isdir(path):
        walkDir(path, settings, silent=silent, tmdbid=args.get('tmdbid'), tvdbid=args.get('tvdbid'), imdbid=args.get('imdbid'), preserveRelative=args['preserverelative'], tag=settings.tagfile, tagonly=args.get('tagonly', False), optionsOnly=args['optionsonly'], processedList=processedList, processedArchive=processedArchive)
    elif (os.path.isfile(path)):
        mp = MediaProcessor(settings, logger=log)
        info = mp.isValidSource(path)
        if info:
            if (args['optionsonly']):
                displayOptions(path, settings)
                return
            try:
                processFile(path, mp, info=info, silent=silent, tag=settings.tagfile, tagonly=args.get('tagonly', False), tmdbid=args.get('tmdbid'), tvdbid=args.get('tvdbid'), imdbid=args.get('imdbid'), season=args.get('season'), episode=args.get('episode'), original=args.get('original'), processedList=processedList, processedArchive=processedArchive)
            except SkipFileException:
                log.debug("Skipping file %s" % path)

        else:
            log.info("File %s is not in a valid format" % (path))
    else:
        log.info("File %s does not exist" % (path))


if __name__ == '__main__':
    main()
