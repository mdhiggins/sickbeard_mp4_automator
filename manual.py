#!/usr/bin/env python
#
import sys
import os
from readSettings import ReadSettings
from tvdb_mp4 import Tvdb_mp4
from tmdb_mp4 import tmdb_mp4
from mkvtomp4 import MkvtoMp4

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")


def mediatype():
    print "Select media type:"
    print "1. Movie (via IMDB ID)"
    print "2. Movie (via TMDB ID)"
    print "3. TV"
    result = raw_input("#: ")
    if result == "1":
        return 1
    elif result == "2":
        return 2
    elif result == "3":
        return 3
    else:
        print "Invalid selection"
        return mediatype()


def getIMDBId():
    print "Enter IMDB ID:"
    imdbid = raw_input("#: ")
    return imdbid


def getTMDBId():
    print "Enter TMDB ID:"
    tmdbid = raw_input("#: ")
    return tmdbid


def getTVDBId():
    print "Enter TVDB Series ID:"
    tvdbid = raw_input("#: ")
    return tvdbid


def getSeason():
    print "Enter Season Number:"
    season = raw_input("#: ")
    return season


def getEpisode():
    print "Enter Episode Number:"
    episode = raw_input("#: ")
    return episode


def getinfo():
    m_type = mediatype()
    if m_type is 3:
        tvdbid = getTVDBId()
        season = getSeason()
        episode = getEpisode()
        return m_type, tvdbid, season, episode
    elif m_type is 1:
        imdbid = getIMDBId()
        return m_type, imdbid
    elif m_type is 2:
        tmdbid = getTMDBId()
        return m_type, tmdbid


def main():
    if len(sys.argv) > 2:
        path = str(sys.argv[1])
        if sys.argv[2] == '-tv':
            tvdbid = int(sys.argv[3])
            season = int(sys.argv[4])
            episode = int(sys.argv[5])
            tagmp4 = Tvdb_mp4(tvdbid, season, episode)
            print "Processing %s Season %s Episode %s - %s" %(tagmp4.show, str(tagmp4.season), str(tagmp4.episode), tagmp4.title)
        elif sys.argv[2] == '-m':
            imdbid = sys.argv[3]
            tagmp4 = tmdb_mp4(imdbid)
            print "Processing %s" % (tagmp4.title)
        elif sys.argv[2] == '-tmdb':
            tmdbid = sys.argv[3]
            tagmp4 = tmdb_mp4(None, tmdbid)
            print "Processing %s" % (tagmp4.title)
        else:
            print "Invalid command line input"
    #elif len(sys.argv) == 2:
    #    path = str(sys.argv[1]).replace("\\", "\\\\").replace("\\\\\\\\", "\\\\")
    #    getinfo()
    else:
        print "Enter path to file:"
        path = raw_input("#: ")
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        result = getinfo()
        if result[0] is 1:
            imdbid = result[1]
            tagmp4 = tmdb_mp4(imdbid)
            print "Processing %s" % (tagmp4.title)
        elif result[0] is 2:
            tmdbid = result[1]
            tagmp4 = tmdb_mp4(None, tmdbid)
            print "Processing %s" % (tagmp4.title)
        elif result[0] is 3:
            tvdbid = int(result[1])
            season = int(result[2])
            episode = int(result[3])
            tagmp4 = Tvdb_mp4(tvdbid, season, episode)
            print "Processing %s Season %s Episode %s - %s" % (tagmp4.show, str(tagmp4.season), str(tagmp4.episode), tagmp4.title)
    
    convert = MkvtoMp4(path, FFMPEG_PATH=settings.ffmpeg, FFPROBE_PATH=settings.ffprobe, delete=settings.delete, output_extension=settings.output_extension, relocate_moov=settings.relocate_moov, iOS=settings.iOS, awl=settings.awl, swl=settings.swl, adl=settings.adl, sdl=settings.sdl, audio_codec=settings.acodec, processMP4=settings.processMP4)
    if convert.output is not None:
        tagmp4.setHD(convert.width, convert.height)
        tagmp4.writeTags(convert.output)

        if settings.relocate_moov:
            convert.QTFS()

if __name__ == '__main__':
    main()
