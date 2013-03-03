import os
import sys
import urllib
import StringIO
import tempfile
import time
from imdb import IMDb
from mutagen.mp4 import MP4, MP4Cover
from extensions import valid_output_extensions


class imdb_mp4:
    def __init__(self, imdbid):
        for i in range(3):
            try:
                imdb = IMDb()
                self.movie = imdb.get_movie(imdbid)

                self.title = self.movie['title']
                self.HD = None

                self.genre = self.movie['genre']

                self.description = self.movie['plot'][0].split('::')[0]
                self.shortdescription = self.movie['plot outline']
                self.date = str(self.movie['year'])

                # Generate XML tags for Actors/Writers/Directors/Producers
                self.xml = self.xmlTags()
                break
            except:
                print "Failed to connect to IMDb, trying again in 20 seconds"
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
                    genre = g
                else:
                    genre += ", " + g
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
        mpaa = self.movie['mpaa']
        result = mpaa.split(' ')
        if result[1] in ratings:
            numerical = ratings[result[1]]
            cutoff = len(result[0]) + len(result[1]) + 2
            output = 'mpaa|' + result[1] + '|' + numerical + '|' + mpaa[cutoff:].capitalize()
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
        for a in self.movie['cast'][:5]:
            if a is not None:
                output.write("<dict><key>name</key><string>" + str(a) + "</string></dict>\n")
        output.write(subfooter)
        # Write screenwriters
        output.write(writerheader)
        for w in self.movie['writer'][:5]:
            if w is not None:
                output.write("<dict><key>name</key><string>" + str(w) + "</string></dict>\n")
        output.write(subfooter)
        # Write directors
        output.write(directorheader)
        for d in self.movie['director'][:5]:
            output.write("<dict><key>name</key><string>" + str(d) + "</string></dict>\n")
        output.write(subfooter)
        # Write producers
        output.write(producerheader)
        for p in self.movie['producer'][:5]:
            output.write("<dict><key>name</key><string>" + str(p) + "</string></dict>\n")
        output.write(subfooter)

        # Write final footer
        output.write(footer)
        return output.getvalue()
        output.close()
    #end xmlTags

    def getArtwork(self):
        #Pulls down all the poster metadata for the correct season and sorts them into the Poster object
        try:
            poster = urllib.urlretrieve(self.movie['full-size cover url'], tempfile.gettempdir() + "\poster.jpg")[0]
        except:
            poster = None
        return poster
    #end artwork
#end imdb_mp4


def main():
    if len(sys.argv) > 2:
        mp4 = str(sys.argv[1]).replace("\\", "\\\\").replace("\\\\\\\\", "\\\\")
        imdb_id = str(sys.argv[2])
        imdb_mp4_instance = imdb_mp4(imdb_id)
        if os.path.splitext(mp4)[1][1:] in valid_output_extensions:
            imdb_mp4_instance.writeTags(mp4)
        else:
            print "Wrong file type"

if __name__ == '__main__':
    main()
