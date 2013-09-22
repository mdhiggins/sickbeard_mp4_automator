#!/usr/bin/env python
#
import sys
import os
from readSettings import ReadSettings
import guessit
from tvdb_mp4 import Tvdb_mp4
from tmdb_mp4 import tmdb_mp4
from mkvtomp4 import MkvtoMp4
from tvdb_api import tvdb_api
from tmdb_api import tmdb
from extensions import valid_input_extensions, valid_output_extensions
from extensions import tmdb_api_key

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")

def mediatype():
	print "Select media type:"
	print "1. Movie (via IMDB ID)"
	print "2. Movie (via TMDB ID)"
	print "3. TV (via TVDB ID)"
	result = raw_input("#: ")
	if 0 < int(result) < 4:
		return result
	else:
		print "Invalid selection"
		return mediatype()

def guessInfo(fileName):
	guess = guessit.guess_video_info(fileName)
	if guess["type"] == "movie":
		return tmdbInfo(guess)
	else:
		return tvdbInfo(guess)

def tmdbInfo(guessData):
	tmdb.configure(tmdb_api_key)
	movies = tmdb.Movies(guessData["title"])
	for movie in movies.iter_results():
		#Identify the first movie in the collection that matches exactly the movie title
		foundname = ''.join(e for e in movie["title"] if e.isalnum())
		origname = ''.join(e for e in guessData["title"] if e.isalnum())
		if foundname.lower() == origname.lower():
			print "Matched movie title as: %s %s" % (movie["title"], movie["release_date"])
			movie = tmdb.Movie(movie["id"])
			break
	return "movie", movie.get_id()

def tvdbInfo(guessData):
	seasonNum = guessData["season"]
	episodeNum = guessData["episodeNumber"]
	series = guessData["series"]
	t = tvdb_api.Tvdb()
	show = t[series]
	return "tv", show['id'], seasonNum, episodeNum

def convertTag(path, tagmp4):
	input_extension = os.path.splitext(path)[1][1:]
	if input_extension in valid_input_extensions:
		convert = MkvtoMp4(path, FFMPEG_PATH=settings.ffmpeg, FFPROBE_PATH=settings.ffprobe, delete=settings.delete, output_extension=settings.output_extension, relocate_moov=settings.relocate_moov, iOS=settings.iOS, awl=settings.awl, swl=settings.swl, adl=settings.adl, sdl=settings.sdl, audio_codec=settings.acodec, processMP4=settings.processMP4)
		if convert.output is not None:
			tagmp4.setHD(convert.width, convert.height)
		if settings.relocate_moov:
				convert.QTFS()
		path = convert.output
	tagmp4.writeTags(path)

def moveFile(path):
	print "Adding this section later"

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
	elif m_type is 4:
		guess = guessit.guess_movie_info(file_name)
	elif m_type is 1:
		imdbid = getIMDBId()
		return m_type, imdbid
	elif m_type is 2:
		tmdbid = getTMDBId()
		return m_type, tmdbid

def stageFile(args, path):
		if args[2] == '-tv':
			tvdbid = int(args[3])
			season = int(args[4])
			episode = int(args[5])
			tagmp4 = Tvdb_mp4(tvdbid, season, episode)
			print "Processing %s Season %s Episode %s - %s" %(tagmp4.show, str(tagmp4.season), str(tagmp4.episode), tagmp4.title)
		elif args[2] == '-m':
			imdbid = args[3]
			tagmp4 = tmdb_mp4(imdbid)
			print "Processing %s" % (tagmp4.title)
		elif args[2] == '-tmdb':
			tmdbid = args[3]
			tagmp4 = tmdb_mp4(None, tmdbid)
			print "Processing %s" % (tagmp4.title)
		elif args[2] == '-guess':
			fileName = os.path.basename(path)
			guess = guessInfo(fileName)
			if guess[0] == "movie":
				tagmp4 = tmdb_mp4(None, guess[1])
				print "Processing %s" % (tagmp4.title)
			elif guess[0] == "tv":
				tagmp4 = Tvdb_mp4(int(guess[1]), int(guess[2]), int(guess[3]))
				print "Processing %s Season %s Episode %s - %s" %(tagmp4.show, str(tagmp4.season), str(tagmp4.episode), tagmp4.title)
		convertTag(path, tagmp4)
		else:
			print "Invalid command line input"
    #elif len(sys.argv) == 2:
    #    path = str(sys.argv[1]).replace("\\", "\\\\").replace("\\\\\\\\", "\\\\")
    #    getinfo()


def main():
	if len(sys.argv) > 2:
		path = str(sys.argv[1])
		if os.path.isdir(path):
			for r,d,f in os.walk(path):
			    for file in f:
			        if os.path.splitext(file)[1][1:] in valid_input_extensions or valid_output_extensions:
			            print "-----------------------------------------------"
			            print "converting %s" % (file)
						filepath = os.path.join(r, file)
						os.chmod(filepath, 0777)
						stageFile(sys.argv, filepath)
		elif os.path.isfile(path):
			os.chmod(filepath, 0777)
			stageFile(sys.argv, filepath)
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
#		elif result[0] is 4:
#			fileName = os.path.basename(path)
#			guess = guessInfo(fileName)
#			if guess[0] == "movie":
#				tagmp4 = tmdb_mp4(None, guess[1])
#				print "Processing %s" % (tagmp4.title)
#			elif guess[0] == "tv":
#				tagmp4 = Tvdb_mp4(int(guess[1]), int(guess[2]), int(guess[3]))
#				print "Processing %s Season %s Episode %s - %s" %(tagmp4.show, str(tagmp4.season), str(tagmp4.episode), tagmp4.title)
		convertTag(path, tagmp4)

if __name__ == '__main__':
	main()
