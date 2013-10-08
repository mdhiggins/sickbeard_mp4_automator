#!/usr/bin/env python
#
import sys
import os
import guessit
import locale
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


def getinfo(fileName=None, silent=False, guess=True):
    '''if type(fileName) is str:
        fileName = fileName.decode(sys.stdout.encoding)'''
    # Try to guess the file is guessing is enabled
    if fileName is not None and guess:
        tagdata = guessInfo(fileName)
        # If the guess returned something, proceed
        if tagdata is not None:
            # If script is running in silent mode, skip confirmation, otherwise confirm.
            if silent:
                return tagdata
            else:
                print "Proceed using guessed identification from filename?"
                if getYesNo() and guess:
                    return tagdata
        else:
            print "Unable to guess based on filename"
    if silent is False:
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
        # Probably add a setting in the future to control this behavior
        return None


def guessInfo(fileName):
    if not settings.fullpathguess:
        fileName = os.path.basename(fileName)
    guess = guessit.guess_video_info(fileName)
    try:
        if guess['type'] == 'movie':
            return tmdbInfo(guess)
        elif  guess['type'] == 'episode':
            return tvdbInfo(guess)
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


def tvdbInfo(guessData):
    series = guessData["series"]
    season = guessData["season"]
    episode = guessData["episodeNumber"]
    t = tvdb_api.Tvdb()
    tvdbid = t[series]['id']
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
        inputfile = inputfile.encode(locale.getpreferredencoding(), errors='replace')
    except: 
        pass
    if MkvtoMp4(settings).validSource(inputfile):
        converter = MkvtoMp4(settings)
        output = converter.process(inputfile, True)
        if tagmp4 is not None:
            tagmp4.setHD(output['x'], output['y'])
            tagmp4.writeTags(output['output'])
            if settings.relocate_moov:
                converter.QTFS(output['output'])
        if settings.copyto:
            converter.replicate(output['output'])


def walkDir(dir, silent=False, output_dir=None):
    for r,d,f in os.walk(dir):
        for file in f:
            filepath = os.path.join(r, file)
            print "Processing file %s" % (filepath)
            try:
                if MkvtoMp4(settings).validSource(filepath):
                    tagdata = getinfo(filepath, silent)
                    processFile(filepath, tagdata)
                else:
                    print "Skipping %s - unrecognized filetype" % (filepath)
            except Exception as e:
                print "An unexpected error occurred, processing of this file has failed"
                print str(e)


def main():
    silent = True if '-silent' in sys.argv else False
    # Override output_dir settings if -nomove switch is used
    #if '-nomove' in sys.argv: settings.output_dir = None 
    if len(sys.argv) > 2:
        path = str(sys.argv[1]).decode(locale.getpreferredencoding())
        # Gather info from command line
        if os.path.isdir(path):
            walkDir(path, silent)
        elif os.path.isfile(path):
            if MkvtoMp4(settings).validSource(path):
                if sys.argv[2] == '-tv':
                    tvdbid = int(sys.argv[3])
                    season = int(sys.argv[4])
                    episode = int(sys.argv[5])
                    tagdata = [3, tvdbid, season, episode]
                elif sys.argv[2] == '-m':
                    imdbid = sys.argv[3]
                    tagdata = [1, imdbid]
                elif sys.argv[2] == '-tmdb':
                    tmdbid = sys.argv[3]
                    tagdata = [2, tmdbid]
                else:
                    tagdata = getinfo(path, silent)
                processFile(path, tagdata)
            else:
                print "File %s is not in the correct format" % (path)
        else:
            print "Invalid command line input"
    # Ask for the info
    else:
        path = os.path.normpath(getValue("Enter path to file"))
        if os.path.isdir(path):
            walkDir(path, silent)
        else:
            if MkvtoMp4(settings).validSource(path):
                tagdata = getinfo(path, silent=silent)
                processFile(path, tagdata)
            else:
                print "File %s is not in the correct format" % (path)
                main()

if __name__ == '__main__':
    main()
