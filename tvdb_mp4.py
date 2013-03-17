import os
import sys
import urllib
import StringIO
import tempfile
import time
from tvdb_api.tvdb_api import Tvdb
from mutagen.mp4 import MP4, MP4Cover
from extensions import valid_output_extensions


class Tvdb_mp4:
    def __init__(self, show, season, episode):
        attempts = 0
        # Set blanks
        self.show = ""
        self.genre = ""
        self.network = ""
        self.title = ""
        self.description = ""
        while attempts < 3:
            try:
                self.tvdb_show = Tvdb(interactive=False, cache=False, banners=True, actors=True, forceConnect=True)
                self.show = show
                self.season = season
                self.episode = episode
                self.HD = None

                #Gather information from theTVDB
                self.showdata = self.tvdb_show[self.show]
                self.seasondata = self.showdata[self.season]
                self.episodedata = self.seasondata[self.episode]

                self.show = self.showdata['seriesname']
                self.genre = self.showdata['genre']
                self.network = self.showdata['network']

                self.title = self.episodedata['episodename']
                self.description = self.episodedata['overview']
                self.airdate = self.episodedata['firstaired']
                self.director = self.episodedata['director']
                self.writer = self.episodedata['writer']

                #Generate XML tags for Actors/Writers/Directors
                self.xml = self.xmlTags()
                break
            except:
                print "Failed to connect to TVDB, trying again in 20 seconds"
                time.sleep(20)
                attempts += 1
        #end __init__

    def writeTags(self, mp4Path):
        print "Tagging file :" + mp4Path
        ext = os.path.splitext(mp4Path)[1][1:]
        if ext not in valid_output_extensions:
            print "Error: File is not the correct format"
            sys.exit()
        try:
            MP4(mp4Path).delete()
        except IOError:
            print "Unable to clear original tags, attempting to proceed"

        video = MP4(mp4Path)
        video["tvsh"] = self.show  # TV show title
        video["\xa9nam"] = self.title  # Video title
        video["tven"] = self.title  # Episode title
        video["desc"] = self.description  # Short description
        video["ldes"] = self.description  # Long description (same a short for tv)
        video["tvnn"] = self.network  # Network
        if self.airdate != "0000-00-00":
            video["\xa9day"] = self.airdate  # Airdate
        video["tvsn"] = [self.season]  # Season number
        video["\xa9alb"] = self.show + ", Season " + str(self.season)  # iTunes Album as Season
        video["tves"] = [self.episode]  # Episode number
        video["trkn"] = [(int(self.episode), len(self.seasondata))]  # Episode number iTunes
        video["stik"] = [10]  # TV show iTunes category
        if self.HD is not None:
            video["hdvd"] = self.HD
        if self.genre is not None:
            video["\xa9gen"] = self.genre.replace('|', ',')[1:-1]  # Genre(s)
        video["----:com.apple.iTunes:iTunMOVI"] = self.xml  # XML - see xmlTags method

        path = self.getArtwork()
        if path is not None:
            cover = open(path, 'rb').read()
            if path.endswith('png'):
                video["covr"] = [MP4Cover(cover, MP4Cover.FORMAT_PNG)]  # png poster
            else:
                video["covr"] = [MP4Cover(cover, MP4Cover.FORMAT_JPEG)]  # jpeg poster
        video["\xa9too"] = "Sickbeard MP4 Automator MDH"
        video.pprint()
        MP4(mp4Path).delete(mp4Path)
        for i in range(3):
            try:
                print "Trying to write tags"
                video.save()
                print "Tags written successfully"
                break
            except IOError:
                print IOError
                time.sleep(5)

    def setHD(self, width, height):
        if width >= 1920 or height >= 1080:
            self.HD = [2]
        elif width >= 1280 or height >= 720:
            self.HD = [1]
        else:
            self.HD = [0]

    def xmlTags(self):
        #constants
        header = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\"><plist version=\"1.0\"><dict>\n"
        castheader = "<key>cast</key><array>\n"
        writerheader = "<key>screenwriters</key><array>\n"
        directorheader = "<key>directors</key><array>\n"
        subfooter = "</array>\n"
        footer = "</dict></plist>\n"

        output = StringIO.StringIO()
        output.write(header)

        # Write actors
        output.write(castheader)
        for a in self.showdata['_actors'][:5]:
            if a is not None:
                output.write("<dict><key>name</key><string>" + a['name'].encode('ascii', errors='ignore') + "</string></dict>\n")
        output.write(subfooter)

        # Write screenwriterr
        if self.writer is not None:
            output.write(writerheader)
            for name in self.writer.split("|"):
                if name != "":
                    output.write("<dict><key>name</key><string>" + name.encode('ascii', errors='ignore') + "</string></dict>\n")
            output.write(subfooter)

        # Write directors
        if self.director is not None:
            output.write(directorheader)
            for name in self.director.split("|"):
                if name != "":
                    output.write("<dict><key>name</key><string>" + name.encode('ascii', errors='ignore') + "</string></dict>\n")
            output.write(subfooter)

        # Close XML
        output.write(footer)
        return output.getvalue()

    def getArtwork(self):
        # Pulls down all the poster metadata for the correct season and sorts them into the Poster object
        posters = posterCollection()
        try:
            for bannerid in self.showdata['_banners']['season']['season'].keys():
                if str(self.showdata['_banners']['season']['season'][bannerid]['season']) == str(self.season):
                    poster = Poster()
                    poster.ratingcount = int(self.showdata['_banners']['season']['season'][bannerid]['ratingcount'])
                    if poster.ratingcount > 0:
                        poster.rating = float(self.showdata['_banners']['season']['season'][bannerid]['rating'])
                    poster.bannerpath = self.showdata['_banners']['season']['season'][bannerid]['_bannerpath']
                    posters.addPoster(poster)
            poster = urllib.urlretrieve(posters.topPoster().bannerpath, tempfile.gettempdir() + "\poster.jpg")[0]
        except:
            poster = None
        return poster


class Poster:
    # Simple container for all the poster parameters needed
    def __init__(self, rating=0, ratingcount=0, bannerpath=""):
        self.rating = rating
        self.bannerpath = bannerpath
        self.ratingcount = ratingcount


class posterCollection:
    def __init__(self):
        self.posters = []

    def topPoster(self):
        # Determines which poster has the highest rating, returns the Poster object
        top = None
        for poster in self.posters:
            if top is None:
                top = poster
            elif poster.rating > top.rating:
                top = poster
            elif poster.rating == top.rating and poster.ratingcount > top.ratingcount:
                top = poster
        return top

    def addPoster(self, inputPoster):
        self.posters.append(inputPoster)


def main():
    if len(sys.argv) > 4:
        mp4 = str(sys.argv[1]).replace("\\", "\\\\").replace("\\\\\\\\", "\\\\")
        tvdb_id = str(sys.argv[2])
        if tvdb_id.isdigit():
            tvdb_id = int(tvdb_id)
        tvdb_season = int(sys.argv[3])
        tvdb_episode = int(sys.argv[4])
        tvdb_mp4_instance = Tvdb_mp4(show=tvdb_id, season=tvdb_season, episode=tvdb_episode)
        if os.path.splitext(mp4)[1][1:] in valid_output_extensions:
            tvdb_mp4_instance.writeTags(mp4)
        else:
            print "Wrong file type"

if __name__ == '__main__':
    main()
