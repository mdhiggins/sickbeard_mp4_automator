#!/usr/bin/env python
import os
import sys
import autoProcessMovie
import guessit
import shutil
from tmdb_api import tmdb
from tmdb_mp4 import tmdb_mp4
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4
from extensions import tmdb_api_key

print "nzbToCouchPotato MP4 edition"


def FILEtoIMDB(file_name):
    """
    Added function by nctiggy. This executes if the nzb does not have the IMDB id appended to the name
    This does capture all of the movies info not just the IMDB id
    """

    print "CouchPotatoServer did not append the IMDB id to the nzb, guessing instead"

    # Guessing at the name of the movie using the filename
    movie_info = guessit.guess_movie_info(file_name)

    #configuring tmdb to use the supplied api key
    tmdb.configure(tmdb_api_key)
    print "Guessed movie title as: %s" % (movie_info["title"])

    #Creating a collection of movies from tmdb for the guess movie title
    movies = tmdb.Movies(movie_info["title"])

    #parse through all movies found
    for movie in movies.iter_results():
        #Identify the first movie in the collection that matches exactly the movie title
        foundname = ''.join(e for e in movie["title"] if e.isalnum())
        origname = ''.join(e for e in movie_info["title"] if e.isalnum())
        if foundname.lower() == origname.lower():
            print "Matched movie title as: %s %s" % (movie["title"], movie["release_date"])
            movie = tmdb.Movie(movie["id"])
            break
    #return the imdb id of the movie identified
    return movie.get_imdb_id()


def NZBtoIMDB(nzbName):
    nzbName = str(nzbName)
    a = nzbName.find('.cp(tt') + 4
    b = nzbName[a:].find(')') + a
    imdbid = nzbName[a:b]
    return imdbid

if len(sys.argv) > 3:
    settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
    imdb_id = NZBtoIMDB(sys.argv[2])
    converter = MkvtoMp4(settings)
    path = str(sys.argv[1])
    moviefile = None
    maxsize = 0
    for r, d, f in os.walk(path):
        for files in f:
            inputfile = os.path.join(r, files)
            
            if MkvtoMp4(settings).validSource(inputfile):
                size = os.path.getsize(inputfile)
                if size > maxsize:
                    moviefile = inputfile
                    maxsize = size

    if moviefile:
        output = converter.process(inputfile)
        # Tag with metadata
        if settings.tagfile:
            if imdb_id == "":
                try:
                    print "Going to guess the following files info: %s" % (sys.argv[2])
                    imdb_id = FILEtoIMDB(os.path.basename(sys.argv[2]))
                except:
                    print "Unable to accurately identify movie file %s" % (inputfile)
            print "IMDB ID is: %s" % (imdb_id)
            try:
                imdbmp4 = tmdb_mp4(imdb_id)
                imdbmp4.setHD(output['x'], output['y'])
                imdbmp4.writeTags(output['output'])
                converter.QTFS(output['output'])
            except AttributeError:
                print "Unable to tag file, Couch Potato probably screwed up passing the IMDB ID"
        # Copy to additional locations
        converter.replicate(output['output'])


# SABnzbd
if len(sys.argv) == 8:
# SABnzbd argv:
# 1 The final directory of the job (full path)
# 2 The original name of the NZB file
# 3 Clean version of the job name (no path info and ".nzb" removed)
# 4 Indexer's report number (if supported)
# 5 User-defined category
# 6 Group that the NZB was posted in e.g. alt.binaries.x
# 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    print "Script triggered from SABnzbd, starting autoProcessMovie..."
    autoProcessMovie.process(sys.argv[1], sys.argv[2], sys.argv[7])

# NZBGet
elif len(sys.argv) == 4:
# NZBGet argv:
# 1  The final directory of the job (full path)
# 2  The original name of the NZB file
# 3  The status of the download: 0 == successful
    print "Script triggered from NZBGet, starting autoProcessMovie..."
    autoProcessMovie.process(sys.argv[1], sys.argv[2], sys.argv[3])

else:
    print "Invalid number of arguments received from client."
    print "Running autoProcessMovie as a manual run..."
    autoProcessMovie.process('Manual Run', 'Manual Run', 0)
