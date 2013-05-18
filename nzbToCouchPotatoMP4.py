#!/usr/bin/env python
import os
import sys
import autoProcessMovie
import tmdb
import guessit
from imdb_mp4 import imdb_mp4
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4
from extensions import valid_input_extensions, tmdb_api_key

print "nzbToCouchPotato MP4 edition"

def FILEtoIMDB(file_name): #Added function by nctiggy. This executes if the nzb does not have the IMDB id appended to the name
    #This does capture all of the movies info not just the IMDB id
    #Future can eliminate the calls to IMDB to use this data instead perhaps

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
        if movie["title"].lower() == movie_info["title"].lower():
            print "Matched movie title as: %s %s" % (movie["title"], movie["release_date"])
            movie = tmdb.Movie(movie["id"])
            break
    #return the imdb id of the movie identified
    return movie.get_imdb_id()[2:]

def NZBtoIMDB(nzbName):
    nzbName = str(nzbName)
    a = nzbName.find('.cp(tt') + 6
    b = nzbName[a:].find(')') + a
    imdbid = nzbName[a:b]
    return imdbid

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
imdb_id = NZBtoIMDB(sys.argv[2])

if len(sys.argv) > 3:
    path = str(sys.argv[1])
    for r, d, f in os.walk(path):
        for files in f:
            if os.path.splitext(files)[1][1:] in valid_input_extensions:
                file = os.path.join(r, files)
                if imdb_id == "":
                    try:
                        print "Going to guess the following files info: %s" % (sys.argv[2])
                        imdb_id = FILEtoIMDB(os.path.basename(sys.argv[2]))
                    except:
                        print "Unable to accurately identify movie file %s" % (file)
                print "IMDB ID is: %s" % (imdb_id)
                print "Converting the following file: %s" % (os.path.basename(file))
                convert = MkvtoMp4(file, FFMPEG_PATH=settings.ffmpeg, FFPROBE_PATH=settings.ffprobe, delete=settings.delete, output_extension=settings.output_extension, relocate_moov=settings.relocate_moov, iOS=settings.iOS, awl=settings.awl, swl=settings.swl, adl=settings.adl, sdl=settings.sdl)
                try:
                    imdbmp4 = imdb_mp4(imdb_id)
                    imdbmp4.setHD(convert.width, convert.height)
                    imdbmp4.writeTags(convert.output)
                except AttributeError:
                    print "Unable to tag file, Couch Potato probably screwed up passing the IMDB ID"

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
