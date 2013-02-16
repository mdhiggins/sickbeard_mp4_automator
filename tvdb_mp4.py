import os
import pipes
import sys
import urllib
import StringIO
import tempfile
import time
import tvdb_api
from tvdb_api import tvdb_api
from mutagen.mp4 import MP4, MP4Cover

class Tvdb_mp4:
    def __init__(self, show, season, episode):
        attempts = 0
        while attempts < 3:
            try:
                self.tvdb_show = tvdb_api.Tvdb(interactive=False, cache=False, banners=True, actors=True, forceConnect=True)
                self.show = show
                self.season = season
                self.episode = episode
                
                #Gather information from theTVDB
                self.showdata = self.tvdb_show[self.show]
                self.episodedata = self.showdata[self.season][self.episode]
                #episodedata = self.tvdb_show[self.show][self.season][self.episode]
                
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
        if not mp4Path.endswith('mp4') and not mp4Path.endswith('m4v'):
            print "Error: File is not the correct format"
            return
        ##Artwork will also require additional processing -- see artwork
        path = self.getArtwork()
        cover = open(path, 'rb').read()
                
        video=MP4(mp4Path)
        video["tvsh"] = self.show #TV show title
        video["\xa9nam"] = self.title #Video title
        video["tven"] = self.title #Episode title
        video["desc"] = self.description #Short description
        video["ldes"] = self.description #Long description (same a short for tv)
        video["tvnn"] = self.network #Network
        if self.airdate != "0000-00-00":
            video["\xa9day"] = self.airdate #Airdate
        video["tvsn"] = [self.season] #Season number
        video["tves"] = [self.episode] #Episode number
        video["stik"] = [10] #TV show iTunes category
        if self.genre != None:
            video["\xa9gen"] = self.genre.replace('|',',')[1:-1] #Genre(s)
        video["----:com.apple.iTunes:iTunMOVI"] = self.xml #XML - see xmlTags method
        if path.endswith('png'):
            video["covr"] = [MP4Cover(cover, MP4Cover.FORMAT_PNG)] #png poster
        else:
            video["covr"] = [MP4Cover(cover, MP4Cover.FORMAT_JPEG)] #jpeg poster

        video.pprint()
        attempts = 0
        while attempts < 3:
            try:
                print "Trying to write tags"
                MP4(mp4Path).delete(mp4Path)
                video.save()
                print "Tags written successfully"
                break
            except IOError:
                print "Failed"
                time.sleep(5)
                attempts += 1
    #end writeTags
    
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
        output.write(castheader)
        
        count = 0
        #Write Actors
        while (count < len(self.showdata['_actors'])-1):
            name = self.showdata['_actors'][count]['name']
            if name != None:
                output.write("<dict><key>name</key><string>" + name.encode('ascii', errors='ignore') + "</string></dict>\n")
            count = count+1
        output.write(subfooter)
        #write Screenwriter
        if self.writer != None:
            output.write(writerheader)
            for name in self.writer.split("|"):
                output.write("<dict><key>name</key><string>" + name.encode('ascii', errors='ignore') + "</string></dict>\n")
            output.write(subfooter)
        #write Director
        if self.director != None:
            output.write(directorheader)
            for name in self.director.split("|"):
                output.write("<dict><key>name</key><string>" + name.encode('ascii', errors='ignore') + "</string></dict>\n")
            output.write(subfooter)
        output.write(footer)
        return output.getvalue()
        output.close()
    #end xmlTags
    
    def getArtwork(self):
        #Pulls down all the poster metadata for the correct season and sorts them into the Poster object
        posters = posterCollection()
        for bannerid in self.showdata['_banners']['season']['season'].keys():
            if str(self.showdata['_banners']['season']['season'][bannerid]['season']) == str(self.season):
                poster = Poster()
                poster.ratingcount = int(self.showdata['_banners']['season']['season'][bannerid]['ratingcount'])
                if poster.ratingcount > 0:
                    poster.rating = float(self.showdata['_banners']['season']['season'][bannerid]['rating'])
                poster.bannerpath = self.showdata['_banners']['season']['season'][bannerid]['_bannerpath']
                posters.addPoster(poster)
        return urllib.urlretrieve(posters.topPoster().bannerpath, tempfile.gettempdir() + "\poster.jpg")[0]
    #end artwork
#end tvdb_mp4

class Poster:
    #simple container for all the poster parameters needed
    def __init__(self, rating = 0, ratingcount = 0, bannerpath = ""):
        self.rating = rating
        self.bannerpath = bannerpath
        self.ratingcount = ratingcount
        #self.language
    #end poster

class posterCollection:
    def __init__(self):
        self.posters = []
    def topPoster(self):
        #Determines which poster has the highest rating, returns the Poster object
        top = Poster()
        for poster in self.posters:
            if poster.rating > top.rating:
                top = poster
            if poster.rating == top.rating and poster.ratingcount > top.ratingcount:
                top = poster
        return top
    def addPoster(self, inputPoster):
        self.posters.append(inputPoster)
    
def main():
    if len(sys.argv) > 3:
        tvdb_instance = tvdb_api.Tvdb(interactive=False, cache=False, banners=True, actors=True)
        mp4 = str(sys.argv[1]).replace("\\","\\\\").replace("\\\\\\\\","\\\\")
        tvdb_id = str(sys.argv[3])
        if tvdb_id.isdigit():
            tvdb_id = int(tvdb_id)
        tvdb_season = int(sys.argv[4])
        tvdb_episode = int(sys.argv[5])
        tvdb_mp4_instance = Tvdb_mp4(show=tvdb_id, season=tvdb_season, episode=tvdb_episode)
        if mp4.endswith(".mp4") or mp4.endswith(".m4v"):
            tvdb_mp4_instance.writeTags(mp4)
        else:
            print "Wrong file type (must be .mp4 or .m4v)"

if __name__ == '__main__':
    main()    