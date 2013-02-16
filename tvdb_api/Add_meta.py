import sys, os, tvdb_api, subprocess, ntpath, shutil, httplib, urllib, logging, logging.handlers

# NOTE:
# In order to run this program correctly, input files must have the following naming convention
# {show Name} - S{01}E{04} 								-> The "series id" must contain all 6 characters to work correctly
# and you should have this have this package installed  ->  https://github.com/dbr/tvdb_api 

# Useful packages:
# https://github.com/dbr/tvnamer --> Renames files to meet the previously mentioned criteria
# https://github.com/dbr/tvdb_api --> Gives this program access to the tvdb api
 
# Before running this program, you will aslo need to have a folder that contains .jpg images you want 
# the album artwork to be set to. The pictures should follow this naming convention {show name}.jpg
# exp: American Idol.jpg

# Variables
tvdb = tvdb_api.Tvdb()
file_w_path = sys.argv[1]
fileName = ntpath.basename(sys.argv[1])


# File Paths *** THESE MUST BE SET BEFORE RUNNING THE PROGRAM ***

# Path to your add to iTunes folder (automatically adds files to iTunes) 
iTunes = "C:\Users\Bob\Desktop"

# Path to the folder where you want files that didn't have metadata successfully written
error = "C:\Users\Bob\Desktop"

# Path to the folder you want error logs to be written to
logPath = "C:\Users\Bob\Desktop"

# Path to folder containing album artwork
artPath = "C:\Users\Bob\Dropbox\Artwork\\"


# Pushover Notification Variables 
#pushover = "enabled"
pushover = "disabled"	
priority = 1
user = ""
token = ""

# priority < -1 = No alert but message gets pushed, priority > 1 = Alert and push message

# Error handling
format_data = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(filename=error+'\Add_Meta.log',level=logging.INFO,format=format_data)

# Unicode -> ascii punctuation substitutions (left/right + single/double quotes)
punctuation = {0x2018:0x27, 0x2019:0x27, 0x201C:0x22, 0x201D:0x22}

# Show Name
index = fileName.find("-")
show = fileName[0:index-1]

# Artwork 
artwork = artPath + show + ".jpg"

# Episode ID
episodeID = fileName[index+2:index+8]

# Season Number
if episodeID[1] == "0":
	season = episodeID[2]
else:
	season = episodeID[1:3]

# Episode Number
if episodeID[4] == "0":
	episode = episodeID[5]
else:
	episode = episodeID[4:6]

# Episode Title
title = tvdb[show][int(season)][int(episode)]['episodename']

# Network
network = tvdb[show]['network']

# Episode Description
description = tvdb[show][int(season)][int(episode)]['overview']
#description = description.translate(punctuation).encode('ascii','ignore')

# Series Parental Rating
rating = tvdb[show]['contentrating']

# Original Air Date
airDate = tvdb[show][int(season)][int(episode)]['firstaired']

# Show Genre
genre = (tvdb[show]['genre'])[1:len(tvdb[show]['genre'])]
genre = genre[0:genre.find("|")]

# Frequently Used File Information
fileInfo =  show + " - " + episodeID

try:
	subprocess.call(["AtomicParsley", file_w_path, "--overWrite", "--artwork", artwork, "--TVShowName", show, "--TVSeasonNum", season, "--TVEpisodeNum", episode, "--title", title, "--TVNetwork", network, "--desc", description, "--longdesc", description, "--contentRating", rating, "--year", airDate, "--genre", genre, "--track", episode, "--disk", season, "--hdvideo", "true", "--stik", "TV Show"])
	logging.info("Metadata successfully set for - "+ fileInfo)
	# Non-overwriting
	#subprocess.call(["AtomicParsley", file_w_path, "--artwork", artwork, "--TVShowName", show, "--TVSeasonNum", season, "--TVEpisodeNum", episode, "--title", title, "--TVNetwork", network, "--desc", description, "--longdesc", description, "--contentRating", rating, "--year", airDate, "--genre", genre, "--track", episode, "--disk", season, "--hdvideo", "true", "--stik", "TV Show"])

except Exception, err:
	logging.error("\"" + fileInfo + "\"   Error: " + str(err))

	# Send message to pushover
	if pushover == "enabled":
		conn = httplib.HTTPSConnection("api.pushover.net:443")
		conn.request("POST", "/1/messages.json",
	  	urllib.urlencode({
	    	"token": token,
	   	"user": user,
	    	"message": "Error: Could not add " + fileInfo + " to iTunes.",
	    	"priority": priority
	 	}), { "Content-type": "application/x-www-form-urlencoded" })
		conn.getresponse()

	# Moves file to Error folder
	#shutil.move(file_w_path, error)

else:
	# Moves file into iTunes
	logging.info(fileInfo + " - added to iTunes.")
	#shutil.move(file_w_path, iTunes)