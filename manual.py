#!/usr/bin/env python

import sys
import os
import guessit
import locale
import glob
import argparse
from readSettings import ReadSettings
from tvdb_mp4 import Tvdb_mp4
from tmdb_mp4 import tmdb_mp4
from mkvtomp4 import MkvtoMp4
from tvdb_api import tvdb_api
from tmdb_api import tmdb
from extensions import tmdb_api_key

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")


def mediatype():
    print "Select media type:"
    print "1. Movie (via IMDB ID)"
    print "2. Movie (via TMDB ID)"
    print "3. TV"
    print "4. Convert without tagging"
    print "5. Skip file"
    result = raw_input("#: ")
    if 0 < int(result) < 6:
        return int(result)
    else:
        print "Invalid selection"
        return mediatype()


def getValue(prompt, num=False):
    print prompt + ":"
    value = raw_input("#: ").strip(' \"')
    # Remove escape characters in non-windows environments
    if os.name != 'nt': value = value.replace('\\', '')
    value = value.decode(sys.stdout.encoding)
    if num is True and value.isdigit() is False:
        print "Must be a numerical value"
        return getValue(prompt, num)
    else:
        return value


def getYesNo():
    yes = ['y', 'yes', 'true', '1']
    no = ['n', 'no', 'false', '0']
    data = raw_input("# [y/n]: ")
    if data.lower() in yes:
        return True
    elif data.lower() in no:
        return False
    else:
        print "Invalid selection"
        return getYesNo()


def getinfo(fileName=None, silent=False, tag=settings.tagfile, tvdbid=None):
    tagdata = None
    # Try to guess the file is guessing is enabled
    if fileName is not None: tagdata = guessInfo(fileName, tvdbid)
    if silent is False:
        if tagdata:
            print "Proceed using guessed identification from filename?"
            if getYesNo():
                return tagdata
        else:
            print "Unable to determine identity based on filename, must enter manually"
        m_type = mediatype()
        if m_type is 3:
            tvdbid = getValue("Enter TVDB Series ID", True)
            season = getValue("Enter Season Number", True)
            episode = getValue("Enter Episode Number", True)
            return m_type, tvdbid, season, episode
        elif m_type is 1:
            imdbid = getValue("Enter IMDB ID")
            return m_type, imdbid
        elif m_type is 2:
            tmdbid = getValue("Enter TMDB ID", True)
            return m_type, tmdbid
        elif m_type is 4:
            return None
        elif m_type is 5:
            return False
    else:
        if tagdata and tag: 
            return tagdata
        else:
            return None


def guessInfo(fileName, tvdbid=None):
    if not settings.fullpathguess:
        fileName = os.path.basename(fileName)
    guess = guessit.guess_video_info(fileName)
    try:
        if guess['type'] == 'movie':
            return tmdbInfo(guess)
        elif  guess['type'] == 'episode':
            return tvdbInfo(guess, tvdbid)
        else:
            return None
    except Exception as e:
        print e
        return None


def tmdbInfo(guessData):
    tmdb.configure(tmdb_api_key)
    movies = tmdb.Movies(guessData["title"].encode('ascii', errors='ignore'), limit=4)
    for movie in movies.iter_results():
        #Identify the first movie in the collection that matches exactly the movie title
        foundname = ''.join(e for e in movie["title"] if e.isalnum())
        origname = ''.join(e for e in guessData["title"] if e.isalnum())
        #origname = origname.replace('&', 'and')
        if foundname.lower() == origname.lower():
            print "Matched movie title as: %s %s" % (movie["title"].encode(sys.stdout.encoding, errors='ignore'), movie["release_date"].encode(sys.stdout.encoding, errors='ignore'))
            movie = tmdb.Movie(movie["id"])
            if isinstance(movie, dict):
                tmdbid = movie["id"]
            else:
                tmdbid = movie.get_id()
            return 2, tmdbid
    return None


def tvdbInfo(guessData, tvdbid=None):
    
    series = guessData["series"]
    season = guessData["season"]
    episode = guessData["episodeNumber"]
    t = tvdb_api.Tvdb()
    #tvdbid = t[series]['id']
    tvdbid = str(tvdbid) if tvdbid else t[series]['id']
    print "Matched TV episode as %s (TVDB ID:%d) S%02dE%02d" % (series.encode(sys.stdout.encoding, errors='ignore'), int(tvdbid), int(season), int(episode))
    return 3, tvdbid, season, episode


def processFile(inputfile, tagdata):
    # Gather tagdata
    if tagdata is False:
        return # This means the user has elected to skip the file
    elif tagdata is None:
        tagmp4 = None # No tag data specified but convert the file anyway
    elif tagdata[0] is 1:
        imdbid = tagdata[1]
        tagmp4 = tmdb_mp4(imdbid)
        print "Processing %s" % (tagmp4.title.encode(sys.stdout.encoding, errors='ignore'))
    elif tagdata[0] is 2:
        tmdbid = tagdata[1]
        tagmp4 = tmdb_mp4(tmdbid, True)
        print "Processing %s" % (tagmp4.title.encode(sys.stdout.encoding, errors='ignore'))
    elif tagdata[0] is 3:
        tvdbid = int(tagdata[1])
        season = int(tagdata[2])
        episode = int(tagdata[3])
        tagmp4 = Tvdb_mp4(tvdbid, season, episode)
        print "Processing %s Season %02d Episode %02d - %s" % (tagmp4.show.encode(sys.stdout.encoding, errors='ignore'), int(tagmp4.season), int(tagmp4.episode), tagmp4.title.encode(sys.stdout.encoding, errors='ignore'))
    
    # Process
    try: 
        inputfile = inputfile.encode(locale.getpreferredencoding())
    except: 
        raise Exception, "File contains an unknown character that cannot be handled by under Python in your operating system, please rename the file"
    if MkvtoMp4(settings).validSource(inputfile):
        converter = MkvtoMp4(settings)
        output = converter.process(inputfile, True)
        if tagmp4 is not None:
            tagmp4.setHD(output['x'], output['y'])
            tagmp4.writeTags(output['output'], settings.artwork)
        if settings.relocate_moov:
            converter.QTFS(output['output'])
        converter.replicate(output['output'])


def walkDir(dir, silent=False, output_dir=None, tvdbid=None):
    for r,d,f in os.walk(dir):
        for file in f:
            filepath = os.path.join(r, file)
            
            try:
                if MkvtoMp4(settings).validSource(filepath):
                    try:
                        print "Processing file %s" % (filepath.encode(sys.stdout.encoding, errors='ignore'))
                    except:
                        try:
                            print "Processing file %s" % (filepath.encode('utf-8', errors='ignore'))
                        except:
                            print "Processing file"
                    tagdata = getinfo(filepath, silent, tvdbid=tvdbid)
                    processFile(filepath, tagdata)
            except Exception as e:
                print "An unexpected error occurred, processing of this file has failed"
                print str(e)


def main():
    parser = argparse.ArgumentParser(description="Manual conversion and tagging script for sickbeard_mp4_automator")
    parser.add_argument('-i', '--input', help='The source that will be converted. May be a file or a directory')
    parser.add_argument('-a', '--auto', action="store_true", help="Enable auto mode, the script will not prompt you for any further input, good for batch files. It will guess the metadata using guessit")
    parser.add_argument('-tv', '--tvdbid', help="Set the TVDB ID for a tv show")
    parser.add_argument('-s', '--season', help="Specifiy the season number")
    parser.add_argument('-e', '--episode', help="Specify the episode number")
    parser.add_argument('-imdb', '--imdbid', help="Specify the IMDB ID for a movie")
    parser.add_argument('-tmdb', '--tmdbid', help="Specify theMovieDB ID for a movie")
    parser.add_argument('-nm', '--nomove', action='store_true', help="Overrides and disables the custom moving of file options that come from output_dir and move-to")
    parser.add_argument('-nc', '--nocopy', action='store_true', help="Overrides and disables the custom copying of file options that come from output_dir and move-to")
    parser.add_argument('-nd', '--nodelete', action='store_true', help="Overrides and disables deleting of original files")

    args = vars(parser.parse_args())

    #Setup the silent mode
    silent = args['auto']

    #Settings overrides
    if (args['nomove']):
        settings.output_dir = None;
        settings.moveto = None;
    if (args['nocopy']):
        settings.copyto = None;
    if (args['nodelete']):
        settings.delete = False;

    #Establish the path we will be working with
    if (args['input']):
        path = str(args['input']).decode(locale.getpreferredencoding())
        try:
            path = glob.glob(path)[0]
        except:
            pass
    else:
        path = getValue("Enter path to file")

    if os.path.isdir(path):
        tvdbid = int(args['tvdbid']) if args['tvdbid'] else None
        walkDir(path, silent, tvdbid=tvdbid)
    elif (os.path.isfile(path) and MkvtoMp4(settings).validSource(path)):
        if (args['tvdbid'] and not (args['imdbid'] or args['tmdbid'])):
            tvdbid = int(args['tvdbid']) if args['tvdbid'] else None
            season = int(args['season']) if args['season'] else None
            episode = int(args['episode']) if args['episode'] else None
            if (tvdbid and season and episode):
                tagdata = [3, tvdbid, season, episode]
            else:
                tagdata = getinfo(path, silent=silent, tvdbid=tvdbid)
        elif ((args['imdbid'] or args['tmdbid']) and not args['tvdbid']):
            if (args['imdbid']):
                imdbid = int(args['imdbid'])
                tagdata = [1, imdbid]
            elif (args['tmdbid']):
                tmdbid = int(args['tmdbid'])
                tagdata = [2, tmdbid]
        else:
            tagdata = getinfo(path, silent=silent)
        processFile(path, tagdata)
    else:
        print "File %s is not in the correct format" % (path)


if __name__ == '__main__':
    main()
