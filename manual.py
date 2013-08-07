import sys
import os
from readSettings import ReadSettings
from tvdb_mp4 import Tvdb_mp4
from tmdb_mp4 import tmdb_mp4
from mkvtomp4 import MkvtoMp4
from extensions import valid_output_extensions

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")

def mediatype():
	print "Select media type:"
	print "1. Movie"
	print "2. TV"
	result = raw_input("#: ")
	if result == "1":
		return 1
	elif result == "2":
		return 2
	else:
		print "Invalid selection"
		return mediatype()

def getIMDBId():
	print "Enter IMDB ID:"
	imdbid = raw_input("#: ")
	return imdbid

def getTVDBId():
	print "Enter TVDB ID:"
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
	if m_type is 2:
		tvdbid = getTVDBId()
		season = getSeason()
		episode = getEpisode()
		return tvdbid, season, episode
	elif m_type is 1:
		imdbid = getIMDBId()
		return [imdbid]


def main():
	m_type = False
	if len(sys.argv) > 2:
		path = str(sys.argv[1]).replace("\\", "\\\\").replace("\\\\\\\\", "\\\\")
		if sys.argv[2] == '-tv':
			m_type = 2
			tvdbid = int(sys.argv[3])
			season = int(sys.argv[4])
			episode = int(sys.argv[5])
		elif sys.argv[2] == '-m':
			m_type = 1
			imdbid = sys.argv[3]
		else:
			print "Invalid command line input"
	#elif len(sys.argv) == 2:
	#	path = str(sys.argv[1]).replace("\\", "\\\\").replace("\\\\\\\\", "\\\\")
	#	getinfo()
	else:
		print "Enter path to file:"
		path = raw_input("#: ").replace("\\", "\\\\").replace("\\\\\\\\", "\\\\")
		result = getinfo()
		if len(result) is 1:
			m_type = 1
			imdbid = result[0]
		elif len(result) is 3:
			m_type = 2
			tvdbid = int(result[0])
			season = int(result[1])
			episode = int(result[2])
	extension = os.path.splitext(path)[1][1:]
	convert = MkvtoMp4(path, FFMPEG_PATH=settings.ffmpeg, FFPROBE_PATH=settings.ffprobe, delete=settings.delete, output_extension=settings.output_extension, relocate_moov=settings.relocate_moov, iOS=settings.iOS, awl=settings.awl, swl=settings.swl, adl=settings.adl, sdl=settings.sdl, audio_codec=settings.acodec)
	if extension not in valid_output_extensions:
		path = convert.output

	if m_type is 1:
		tagmp4 = tmdb_mp4(imdbid)
		tagmp4.writeTags(path)
	elif m_type is 2:
		print season
		print episode
		tagmp4 = Tvdb_mp4(tvdbid, season, episode)
		tagmp4.setHD(convert.width, convert.height)
		tagmp4.writeTags(path)
	else:
		print "Error"

if __name__ == '__main__':
    main()
