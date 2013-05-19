import os
import sys
import urllib
import StringIO
import tempfile
import time
from tmdb_api import tmdb
from mutagen.mp4 import MP4, MP4Cover
from extensions import valid_output_extensions, tmdb_api_key


class tmdb_mp4:
    def __init__(self, imdbid):
        print "Fetching info for imdb id " + str(imdbid)
        for i in range(3):
            try:
                tmdb.configure(tmdb_api_key)

                tmdbid = tmdb.Movies().imdbtotmdb(imdbid)
                self.movie = tmdb.Movie(tmdbid)

                self.HD = None

                self.title = self.movie.get_title()
                self.genre = self.movie.get_genres()

                self.shortdescription = self.movie.get_tagline()
                self.description = self.movie.get_overview()

                self.date = self.movie.get_release_date()

                # Generate XML tags for Actors/Writers/Directors/Producers
                self.xml = self.xmlTags()
                break
            except Exception as e:
                print "Failed to connect to tMDB, trying again in 20 seconds"
                print e
                time.sleep(20)

    def writeTags(self, mp4Path):
        print "Tagging file :" + mp4Path
        ext = os.path.splitext(mp4Path)[1][1:]
        if ext not in valid_output_extensions:
            print "Error: File is not the correct format"
            sys.exit()
        try:
            MP4(mp4Path).delete()
        except IOError:
            print "Unable to clear original tags"

        video = MP4(mp4Path)
        video["\xa9nam"] = self.title  # Movie title
        video["desc"] = self.shortdescription  # Short description
        video["ldes"] = self.description  # Long description
        video["\xa9day"] = self.date  # Year
        video["stik"] = [9]  # Movie iTunes category
        if self.HD is not None:
            video["hdvd"] = self.HD
        if self.genre is not None:
            genre = None
            for g in self.genre:
                if genre is None:
                    genre = g['name']
                else:
                    genre += ", " + g['name']
            video["\xa9gen"] = genre  # Genre(s)
        video["----:com.apple.iTunes:iTunMOVI"] = self.xml  # XML - see xmlTags method
        video["----:com.apple.iTunes:iTunEXTC"] = self.rating()

        path = self.getArtwork()
        if path is not None:
            cover = open(path, 'rb').read()
            if path.endswith('png'):
                video["covr"] = [MP4Cover(cover, MP4Cover.FORMAT_PNG)]  # png poster
            else:
                video["covr"] = [MP4Cover(cover, MP4Cover.FORMAT_JPEG)]  # jpeg poster
        video["\xa9too"] = "MP4 Automator MDH"
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

    def rating(self):
        ratings = {'G': '100',
                        'PG': '200',
                        'PG-13': '300',
                        'R': '400',
                        'NC-17': '500'}
        output = None
        mpaa = self.movie.get_mpaa_rating()
        if mpaa in ratings:
            numerical = ratings[mpaa]
            output = 'mpaa|' + mpaa.capitalize() + '|' + numerical + '|'
        return str(output)

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
        producerheader = "<key>producers</key><array>\n"
        subfooter = "</array>\n"
        footer = "</dict></plist>\n"

        output = StringIO.StringIO()
        output.write(header)

        # Write actors
        output.write(castheader)
        for a in self.movie.get_cast()[:5]:
            if a is not None:
                output.write("<dict><key>name</key><string>" + str(a['name']) + "</string></dict>\n")
        output.write(subfooter)
        # Write screenwriters
        output.write(writerheader)
        for w in self.movie.get_writers()[:5]:
            if w is not None:
                output.write("<dict><key>name</key><string>" + str(w['name']) + "</string></dict>\n")
        output.write(subfooter)
        # Write directors
        output.write(directorheader)
        for d in self.movie.get_directors()[:5]:
            if d is not None:
                output.write("<dict><key>name</key><string>" + str(d['name']) + "</string></dict>\n")
        output.write(subfooter)
        # Write producers
        output.write(producerheader)
        for p in self.movie.get_producers()[:5]:
            if p is not None:
                output.write("<dict><key>name</key><string>" + str(p['name']) + "</string></dict>\n")
        output.write(subfooter)

        # Write final footer
        output.write(footer)
        return output.getvalue()
        output.close()
    #end xmlTags

    def getArtwork(self):
        #Pulls down all the poster metadata for the correct season and sorts them into the Poster object
        try:
            poster = urllib.urlretrieve(self.movie.get_poster(), tempfile.gettempdir() + "\poster.jpg")[0]
        except:
            poster = None
        return poster
    #end artwork
#end tmdb_mp4


def main():
    if len(sys.argv) > 2:
        mp4 = str(sys.argv[1]).replace("\\", "\\\\").replace("\\\\\\\\", "\\\\")
        imdb_id = str(sys.argv[2])
        tmdb_mp4_instance = tmdb_mp4(imdb_id)
        if os.path.splitext(mp4)[1][1:] in valid_output_extensions:
            tmdb_mp4_instance.writeTags(mp4)
        else:
            print "Wrong file type"

if __name__ == '__main__':
    main()
