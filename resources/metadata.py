import os
import sys
import requests
import enum
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import tempfile
import time
import logging
import tmdbsimple as tmdb
from mutagen.mp4 import MP4, MP4Cover, MP4StreamInfoError
from resources.extensions import valid_poster_extensions, tmdb_api_key
from resources.lang import getAlpha2BCode


class TMDBIDError(Exception):
    pass


class MediaType(enum.Enum):
    Movie = "movie"
    TV = "tv"


class Metadata:
    __CONTENTRATINGS = {
        "TV-Y": 'us-tv|TV-Y|100',
        "TV-Y7": 'us-tv|TV-Y7|200',
        "TV-G": 'us-tv|TV-G|300',
        "TV-PG": 'us-tv|TV-PG|400',
        "TV-14": 'us-tv|TV-14|500',
        "TV-MA": 'us-tv|TV-MA|600',
        "G": 'mpaa|G|100',
        "PG": 'mpaa|PG|200',
        "PG-13": 'mpaa|PG-13|300',
        "R": 'mpaa|R|400',
        "NC-17": 'mpaa|NC-17|500'
    }
    __NOTRATED = {
        MediaType.Movie: 'mpaa|Not Rated|000',
        MediaType.TV: 'us-tv|Not Rated|000'
    }
    HD = None

    def __init__(self, mediatype, tmdbid=None, imdbid=None, tvdbid=None, season=None, episode=None, original=None, language=None, logger=None):
        tmdb.API_KEY = tmdb_api_key
        self.log = logger or logging.getLogger(__name__)

        self.log.debug("TMDBID: %s" % tmdbid)
        self.log.debug("IMDBID: %s" % imdbid)
        self.log.debug("TVDBID: %s" % tvdbid)

        self.tmdbid = self.resolveTmdbID(mediatype, tmdbid=tmdbid, tvdbid=tvdbid, imdbid=imdbid)
        self.log.debug("Using TMDB ID: %s" % self.tmdbid)

        if not self.tmdbid:
            self.log.error("Unable to resolve a valid TMDBID.")
            raise TMDBIDError

        self.mediatype = mediatype
        self.language = getAlpha2BCode(language, default='en')
        self.original = original

        if self.mediatype == MediaType.Movie:
            query = tmdb.Movies(self.tmdbid)
            self.moviedata = query.info(language=self.language)
            self.credit = query.credits()
            try:
                releases = query.release_dates()
                release = next(x for x in releases['results'] if x['iso_3166_1'] == 'US')
                rating = release['release_dates'][0]['certification']
                self.rating = self.getRating(rating)
            except:
                self.log.error("Unable to retrieve rating.")
                self.rating = None

            self.title = self.moviedata['title']
            self.genre = self.moviedata['genres']
            self.tagline = self.moviedata['tagline']
            self.description = self.moviedata['overview']
            self.date = self.moviedata['release_date']
        elif self.mediatype == MediaType.TV:
            self.season = int(season)
            self.episode = int(episode)

            seriesquery = tmdb.TV(self.tmdbid)
            seasonquery = tmdb.TV_Seasons(self.tmdbid, season)
            episodequery = tmdb.TV_Episodes(self.tmdbid, season, episode)

            self.showdata = seriesquery.info(language=self.language)
            self.seasondata = seasonquery.info(language=self.language)
            self.episodedata = episodequery.info(language=self.language)
            self.credit = episodequery.credits()

            try:
                content_ratings = seriesquery.content_ratings()
                rating = next(x for x in content_ratings['results'] if x['iso_3166_1'] == 'US')['rating']
                self.rating = self.getRating(rating)
            except:
                self.log.error("Unable to retrieve rating.")
                self.rating = None

            self.showname = self.showdata['name']
            self.genre = self.showdata['genres']
            self.network = self.showdata['networks']
            self.title = self.episodedata['name']
            self.description = self.episodedata['overview']
            self.airdate = self.episodedata['air_date']

    def resolveTmdbID(self, mediatype, tmdbid=None, tvdbid=None, imdbid=None):
        find = None

        if tmdbid:
            try:
                return int(tmdbid)
            except:
                self.log.error("Invalid TMDB ID provided.")
                pass

        if mediatype == MediaType.Movie:
            if imdbid:
                imdbid = "tt%s" % imdbid if not imdbid.startswith("tt") else imdbid
                find = tmdb.Find(imdbid)
                response = find.info(external_source='imdb_id')
            if find and len(find.movie_results) > 0:
                tmdbid = find.movie_results[0].get('id')
        elif mediatype == MediaType.TV:
            if imdbid:
                imdbid = "tt%s" % imdbid if not imdbid.startswith("tt") else imdbid
                find = tmdb.Find(imdbid)
                response = find.info(external_source='imdb_id')
            elif tvdbid:
                find = tmdb.Find(tvdbid)
                response = find.info(external_source='tvdb_id')
            if find and len(find.tv_results) > 0:
                tmdbid = find.tv_results[0].get('id')
        return tmdbid

    def writeTags(self, path, artwork=True, thumbnail=False, width=None, height=None):
        self.log.info("Tagging file: %s." % path)
        if width and height:
            try:
                self.setHD(width, height)
            except:
                self.log.exception("Unable to set HD tag.")

        try:
            video = MP4(path)
        except MP4StreamInfoError:
            self.log.error('File is not a valid MP4 file and cannot be tagged.')
            return False

        try:
            video.delete()
        except:
            self.log.debug("Unable to clear original tags, will proceed.")

        if self.mediatype == MediaType.Movie:
            video["\xa9nam"] = self.title  # Movie title
            video["desc"] = self.tagline  # Short description
            video["ldes"] = self.description  # Long description
            video["\xa9day"] = self.date  # Year
            video["stik"] = [9]  # Movie iTunes category
        elif self.mediatype == MediaType.TV:
            video["tvsh"] = self.showname  # TV show title
            video["\xa9nam"] = self.title  # Video title
            video["tven"] = self.title  # Episode title
            video["desc"] = self.shortDescription  # Short description
            video["ldes"] = self.description  # Long description
            network = [x['name'] for x in self.network]
            video["tvnn"] = network  # Network
            video["\xa9day"] = self.airdate  # Airdate
            video["tvsn"] = [self.season]  # Season number
            video["disk"] = [(self.season, 0)]  # Season number as disk
            video["\xa9alb"] = self.showname + ", Season " + str(self.season)  # iTunes Album as Season
            video["tves"] = [self.episode]  # Episode number
            video["trkn"] = [(self.episode, len(self.seasondata.get('episodes', [])))]  # Episode number iTunes
            video["stik"] = [10]  # TV show iTunes category

        if self.HD:
            video["hdvd"] = self.HD
        if self.genre and len(self.genre) > 0:
            video["\xa9gen"] = self.genre[0].get('name')
        video["----:com.apple.iTunes:iTunMOVI"] = self.xml.encode("UTF-8", errors="ignore")  # XML - see xmlTags method
        if self.rating:
            video["----:com.apple.iTunes:iTunEXTC"] = self.rating.encode("UTF-8", errors="ignore")  # iTunes content rating

        if artwork:
            coverpath = self.getArtwork(path, thumbnail=thumbnail)
            if coverpath is not None:
                cover = open(coverpath, 'rb').read()
                if path.endswith('png'):
                    video["covr"] = [MP4Cover(cover, MP4Cover.FORMAT_PNG)]  # png poster
                else:
                    video["covr"] = [MP4Cover(cover, MP4Cover.FORMAT_JPEG)]  # jpeg poster

        if self.original:
            video["\xa9too"] = "SMA:" + os.path.basename(self.original)
        else:
            video["\xa9too"] = "SMA:" + os.path.basename(path)

        try:
            self.log.info("Trying to write tags.")
            video.save()
            self.log.info("Tags written successfully.")
            return True
        except:
            self.log.exception("There was an error writing the tags.")
        return False

    def setHD(self, width, height):
        if width >= 3800 or height >= 2100:
            self.HD = [3]
        elif width >= 1900 or height >= 1060:
            self.HD = [2]
        elif width >= 1260 or height >= 700:
            self.HD = [1]
        else:
            self.HD = [0]

    @property
    def shortDescription(self):
        if self.description:
            return self.getShortDescription(self.description)
        return ""

    def getShortDescription(self, description, length=255, splitter='.', suffix='.'):
        if len(description) <= length:
            return description
        else:
            return ' '.join(description[:length + 1].split('.')[0:-1]) + suffix

    def getRating(self, rating):
        return self.__CONTENTRATINGS.get(rating.upper(), self.__NOTRATED.get(self.mediatype))

    @property
    def xml(self):
        # constants
        header = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\"><plist version=\"1.0\"><dict>\n"
        castheader = "<key>cast</key><array>\n"
        writerheader = "<key>screenwriters</key><array>\n"
        directorheader = "<key>directors</key><array>\n"
        producerheader = "<key>producers</key><array>\n"
        subfooter = "</array>\n"
        footer = "</dict></plist>\n"

        output = StringIO()
        output.write(header)

        if self.credit:
            # Write actors
            output.write(castheader)
            for a in self.credit['cast'][:5]:
                if a is not None and a['name'] is not None:
                    output.write("<dict><key>name</key><string>%s</string></dict>\n" % a['name'])
            output.write(subfooter)
            # Write screenwriters
            output.write(writerheader)
            for w in [x for x in self.credit['crew'] if x['department'].lower() == "writing"][:5]:
                if w is not None:
                    output.write("<dict><key>name</key><string>%s</string></dict>\n" % w['name'])
            output.write(subfooter)
            # Write directors
            output.write(directorheader)
            for d in [x for x in self.credit['crew'] if x['department'].lower() == "directing"][:5]:
                if d is not None:
                    output.write("<dict><key>name</key><string>%s</string></dict>\n" % d['name'])
            output.write(subfooter)
            # Write producers
            output.write(producerheader)
            for p in [x for x in self.credit['crew'] if x['department'].lower() == "production"][:5]:
                if p is not None:
                    output.write("<dict><key>name</key><string>%s</string></dict>\n" % p['name'])
            output.write(subfooter)

        # Close XML
        output.write(footer)
        return output.getvalue()

    def urlretrieve(self, url, fn):
        with open(fn, 'wb') as f:
            f.write(requests.get(url, allow_redirects=True, timeout=30).content)
        return (fn, f)

    def getArtwork(self, path, thumbnail=False):
        # Check for artwork in the same directory as the source
        poster = None
        base, ext = os.path.splitext(path)
        for e in valid_poster_extensions:
            path = base + os.extsep + e
            if (os.path.exists(path)):
                poster = path
                self.log.info("Local artwork detected, using %s." % path)
                break

        # If no local files are found, attempt to download them
        if not poster:
            poster_path = None
            if self.mediatype == MediaType.Movie:
                poster_path = self.moviedata.get('poster_path')
            elif self.mediatype == MediaType.TV:
                if thumbnail:
                    poster_path = self.episodedata.get('still_path')
                else:
                    poster_path = self.seasondata.get('poster_path')

            if not poster_path:
                self.log.warning("No artwork found for media file.")
                return None

            savepath = os.path.join(tempfile.gettempdir(), "poster-%s.jpg" % (self.tmdbid))

            # Ensure the save path is clear
            if os.path.exists(savepath):
                try:
                    os.remove(savepath)
                except:
                    i = 2
                    while os.path.exists(savepath):
                        savepath = os.path.join(tempfile.gettempdir(), "poster-%s.%d.jpg" % (self.tmdbid, i))
                        i += 1

            try:
                poster = self.urlretrieve("https://image.tmdb.org/t/p/original" + poster_path, savepath)[0]
            except Exception:
                self.log.exception("Exception while retrieving poster" % poster_path)
        return poster
