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
import shutil

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
	print "Guessing %s TVDB info" % (series)
	t = tvdb_api.Tvdb()
	show = t[series]
	return "tv", show['id'], seasonNum, episodeNum

def convertFile(path):
	convert = MkvtoMp4(path, FFMPEG_PATH=settings.ffmpeg, FFPROBE_PATH=settings.ffprobe, delete=settings.delete, output_extension=settings.output_extension, relocate_moov=settings.relocate_moov, iOS=settings.iOS, awl=settings.awl, swl=settings.swl, adl=settings.adl, sdl=settings.sdl, audio_codec=settings.acodec, processMP4=settings.processMP4)
	return convert

def tagFile(tagInfo, fileInfo, path):
	if fileInfo.output is not None:
		tagInfo.setHD(fileInfo.width, fileInfo.height)
		if settings.relocate_moov:
			fileInfo.QTFS()
			path = fileInfo.output
	tagInfo.writeTags(path)

def moveFile(path):
	shutil.move(path, output_directory)

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


def stageFile(path, inputs):
	if inputs is None:
		fileName = os.path.basename(path)
		guess = guessInfo(fileName)
		if guess[0] == "movie":
			tagmp4 = tmdb_mp4(None, guess[1])
			print "Processing %s" % (tagmp4.title)
		elif guess[0] == "tv":
			tagmp4 = Tvdb_mp4(int(guess[1]), int(guess[2]), int(guess[3]))
			print "Processing %s Season %s Episode %s - %s" %(tagmp4.show, str(tagmp4.season), str(tagmp4.episode), tagmp4.title)
	elif inputs[2] is not None:
		tvdbid = inputs[2]
		season = inputs[3]
		episode = inputs[4]
		tagmp4 = Tvdb_mp4(tvdbid, season, episode)
		print "Processing %s Season %s Episode %s - %s" %(tagmp4.show, str(tagmp4.season), str(tagmp4.episode), tagmp4.title)
	elif inputs[0] is not None:
		imdbid = inputs[0]
		tagmp4 = tmdb_mp4(imdbid)
		print "Processing %s" % (tagmp4.title)
	elif inputs[1] is not None:
		tmdbid = inputs[1]
		tagmp4 = tmdb_mp4(None, tmdbid)
		print "Processing %s" % (tagmp4.title)
	else:
		print "Invalid command line input"
		return
	return tagmp4
    #elif len(sys.argv) == 2:
    #    path = str(sys.argv[1]).replace("\\", "\\\\").replace("\\\\\\\\", "\\\\")
    #    getinfo()

def isValidInput(fileName):
	return os.path.splitext(fileName)[1][1:] in valid_input_extensions

def isValidOutput(fileName):
	return os.path.splitext(fileName)[1][1:] in valid_output_extensions

def iteratePath(path, inputs)
	for r,d,f in os.walk(path):
		for file in f:
			filepath = os.path.join(r, file)
			os.chmod(filepath, 0777)
			processFile(filepath, inputs)

def convertArguments(args):
	if args[2] == '-tv':
		tvdbid = int(args[3])
		season = int(args[4])
		episode = int(args[5])
		inputs = (None, None, tvdbid, season, episode)
	elif args[2] == '-m':
		imdbid = args[3]
		inputs = (imdbid, None, None, None, None)
	elif args[2] == '-tmdb':
		tmdbid = args[3]
		inputs = (None, tmdbid, None, None, None)
	elif: args[2] == '-guess':
		inputs = None
	return inputs

def convertInput(results):
	if results[0] is 3:
		tvdbid = int(result[1])
		season = int(result[2])
		episode = int(result[3])
		inputs = (None, None, tvdbid, season, episode
	elif results[0] is 1:
		imdbid = result[1]
		inputs = (imdbid, None, None, None, None)
	elif results[0] is 2:
		tmdbid = result[1]
		inputs = (None, tmdbid, None, None, None)
	elif results[0] is 4:
		inputs = None
	return inputs

def processFile(filepath, inputs):
	fileName = os.path.basname(filepath)
	if isValidInput(fileName):
		tagInfo = stageFile(filepath, inputs)
		fileInfo = convertFile(filepath)
		tagFile(tagInfo, fileInfo, None)
		moveFile(fileInfo.output)
	elif isValidOutput(fileName):
		tagInfo = stageFile(filepath, inputs)
		tagFile(tagInfo, None, filepath)
		moveFile(filepath)

def main():
	if len(sys.argv) > 2:
		path = str(sys.argv[1])
		inputs = convertArguments(sys.argv)
		if sys.argv[2] == "-guess":
			if os.path.isdir(path):
				iteratePath(path, inputs)
			elif os.path.isfile(path):
				os.chmod(path, 0777)
				processFile(path, inputs)
		elif os.path.isdir(path):
			print "Please specify a file or use the -guess flag"
		else:
			os.chmod(path, 0777)
			processFile(path, inputs)
	else:
		print "Enter path to file:"
		path = raw_input("#: ")
		if path.startswith('"') and path.endswith('"'):
			path = path[1:-1]
			result = getinfo()
		inputs = convertInput(result)
		os.chmod(path, 0777)
		processFile(path, inputs)

#		elif result[0] is 4:
#			fileName = os.path.basename(path)
#			guess = guessInfo(fileName)
#			if guess[0] == "movie":
#				tagmp4 = tmdb_mp4(None, guess[1])
#				print "Processing %s" % (tagmp4.title)
#			elif guess[0] == "tv":
#				tagmp4 = Tvdb_mp4(int(guess[1]), int(guess[2]), int(guess[3]))
#				print "Processing %s Season %s Episode %s - %s" %(tagmp4.show, str(tagmp4.season), str(tagmp4.episode), tagmp4.title)

if __name__ == '__main__':
	main()
