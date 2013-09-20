#!/usr/bin/env python
#-*- coding:utf-8 -*-
#author:doganaydin
#project:themoviedb
#repository:http://github.com/doganaydin/themoviedb
#license: LGPLv3 http://www.gnu.org/licenses/lgpl.html
"""An interface to the themoviedb.org API"""

__author__ = "doganaydin"
__version__ = "1.0b"

try:
    import simplejson
except:
    import json as simplejson

import fuzzywuzzy.fuzz
import requests

config = {}

def configure(api_key, language='en'):
    config['apikey'] = api_key
    config['language'] = language
    config['urls'] = {}
    config['urls']['movie.search'] = "https://api.themoviedb.org/3/search/movie?query=%%s&api_key=%(apikey)s&page=%%s" % (config)
    config['urls']['movie.info'] = "https://api.themoviedb.org/3/movie/%%s?api_key=%(apikey)s" % (config)
    config['urls']['people.search'] = "https://api.themoviedb.org/3/search/person?query=%%s&api_key=%(apikey)s&page=%%s" % (config)
    config['urls']['collection.info'] = "https://api.themoviedb.org/3/collection/%%s&api_key=%(apikey)s" % (config)
    config['urls']['movie.alternativetitles'] = "https://api.themoviedb.org/3/movie/%%s/alternative_titles?api_key=%(apikey)s" % (config)
    config['urls']['movie.casts'] = "https://api.themoviedb.org/3/movie/%%s/casts?api_key=%(apikey)s" % (config)
    config['urls']['movie.images'] = "https://api.themoviedb.org/3/movie/%%s/images?api_key=%(apikey)s" % (config)
    config['urls']['movie.keywords'] = "https://api.themoviedb.org/3/movie/%%s/keywords?api_key=%(apikey)s" % (config)
    config['urls']['movie.releases'] = "https://api.themoviedb.org/3/movie/%%s/releases?api_key=%(apikey)s" % (config)
    config['urls']['movie.trailers'] = "https://api.themoviedb.org/3/movie/%%s/trailers?api_key=%(apikey)s" % (config)
    config['urls']['movie.translations'] = "https://api.themoviedb.org/3/movie/%%s/translations?api_key=%(apikey)s" % (config)
    config['urls']['person.info'] = "https://api.themoviedb.org/3/person/%%s?api_key=%(apikey)s&append_to_response=images,credits" % (config)
    config['urls']['latestmovie'] = "https://api.themoviedb.org/3/latest/movie?api_key=%(apikey)s" % (config)
    config['urls']['config'] = "https://api.themoviedb.org/3/configuration?api_key=%(apikey)s" % (config)
    config['urls']['request.token'] = "https://api.themoviedb.org/3/authentication/token/new?api_key=%(apikey)s" % (config)
    config['urls']['session.id'] = "https://api.themoviedb.org/3/authentication/session/new?api_key=%(apikey)s&request_token=%%s" % (config)
    config['urls']['movie.add.rating'] = "https://api.themoviedb.org/3/movie/%%s/rating?session_id=%%s&api_key=%(apikey)s" % (config)
    config['api'] = {}
    config['api']['backdrop.sizes'] = ""
    config['api']['base.url'] = ""
    config['api']['poster.sizes'] = ""
    config['api']['profile.sizes'] = ""
    config['api']['session.id'] = ""


class Core(object):
    def getJSON(self, url, language=None):
        language = language or config['language']
        page = requests.get(url, params={'language': language}).content
        try:
            return simplejson.loads(page)
        except:
            return simplejson.loads(page.decode('utf-8'))

    def escape(self,text):
        if len(text) > 0:
            return requests.utils.quote(text)
        return False

    def update_configuration(self):
        c = self.getJSON(config['urls']['config'])
        config['api']['backdrop.sizes'] = c['images']['backdrop_sizes']
        config['api']['base.url'] = c['images']['base_url']
        config['api']['poster.sizes'] = c['images']['poster_sizes']
        config['api']['profile.sizes'] = c['images']['profile_sizes']
        return "ok"

    def backdrop_sizes(self,img_size):
        size_list = {'s':'w300','m':'w780','l':'w1280','o':'original'}
        return size_list[img_size]

    def poster_sizes(self,img_size):
        size_list = {'s':'w92','m':'w185','l':'w500','o':'original'}
        return size_list[img_size]

    def profile_sizes(self,img_size):
        size_list = {'s':'w45','m':'185','l':'w632','o':'original'}
        return size_list[img_size]

    def request_token(self):
        req = self.getJSON(config['urls']['request.token'])
        r = req["request_token"]
        return {"url":"http://themoviedb.org/authenticate/%s" % r,"request_token":r}

    def session_id(self,token):
        sess = self.getJSON(config['urls']['session.id'] % token)
        config['api']['session.id'] = sess["session_id"]
        return sess["session_id"]

class Movies(Core):
    def __init__(self, title="", limit=False, language=None):
        self.limit = limit
        self.update_configuration()
        self.searched = title
        title = self.escape(title)
        self.movies = self.getJSON(config['urls']['movie.search'] % (title,str(1)), language=language)
        pages = self.movies["total_pages"]
        if not self.limit:
            if int(pages) > 1:                  #
                for i in range(2,int(pages)+1): #  Thanks @tBuLi
                    self.movies["results"].extend(self.getJSON(config['urls']['movie.search'] % (title,str(i)), language=language)["results"])

    def __iter__(self):
        for i in self.movies["results"]:
            yield Movie(i["id"])

    def get_total_results(self):
        if self.limit:
            return len(self.movies["results"])
        return self.movies["total_results"]

    def iter_results(self):
        for i in self.movies["results"]:
            yield i

    def get_ordered_matches(self):
        """
        Return a list of tuples.  Each tuples first element is a percentage similarity
        between the search term and the tuples second element 'title' value.

        Ordered, descending, by the percentage similarity.
        """
        our_results = []
        for movie in self.iter_results():
            ratio = fuzzywuzzy.fuzz.ratio(self.searched, movie['title'])
            our_results.append((ratio, movie))
        return sorted(our_results, reverse=True)

    def get_best_match(self):
        """
        Returns a tuple whose first element is the percent similarity between the search
        term and the tuple's second element's 'title' value.

        The result is the best-matching result from all the results we get from TMDb.
        """
        try:
            return self.get_ordered_matches()[0]
        except IndexError:
            return

class Movie(Core):
    def __init__(self, movie_id, language=None):
        self.movie_id = movie_id
        self.update_configuration()
        self.movies = self.getJSON(config['urls']['movie.info'] % self.movie_id, language=language)

    def is_adult(self):
        return self.movies['adult']

    def get_collection_id(self):
        return self.movies['belongs_to_collection']["id"]

    def get_collection_name(self):
        return self.movies['belongs_to_collection']["name"]

    # Sizes = s->w300 m->w780 l->w1280 o->original(default)
    def get_collection_backdrop(self,img_size="o"):
        try:
            img_path = self.movies["belongs_to_collection"]["backdrop_path"]
        except KeyError:
            return
        return config['api']['base.url']+self.poster_sizes(img_size)+img_path

    # Sizes = s->w92 m->w185 l->w500 o->original(default)
    def get_collection_poster(self,img_size="o"):
        try:
            img_path = self.movies["belongs_to_collection"]["poster_path"]
        except KeyError:
            return
        return config['api']['base.url']+self.poster_sizes(img_size)+img_path

    def get_budget(self):
        return self.movies['budget']

    def get_genres(self):
        genres = []
        for i in self.movies['genres']:
            genres.append({"id":i["id"],"name":i["name"]})
        return genres

    def get_homepage(self):
        return self.movies['homepage']

    def get_imdb_id(self):
        return self.movies['imdb_id']

    def get_overview(self):
        return self.movies['overview']

    def get_production_companies(self):
        companies = []
        for i in self.movies['production_companies']:
            companies.append({"id":i["id"],"name":i["name"]})
        return companies

    def get_productions_countries(self):
        countries = []
        for i in self.movies['production_countries']:
            countries.append({"iso_3166_1":i["iso_3166_1"],"name":i["name"]})
        return countries

    def get_revenue(self):
        return self.movies['revenue']

    def get_runtime(self):
        return self.movies['runtime']

    def get_spoken_languages(self):
        langs = []
        for i in self.movies['spoken_languages']:
            langs.append({"iso_639_1":i["iso_639_1"],"name":i["name"]})
        return langs

    def get_tagline(self):
        return self.movies['tagline']

    def get_vote_average(self):
        return self.movies['vote_average']

    def get_vote_count(self):
        return self.movies['vote_count']

    def get_id(self):
        return self.movie_id

    # Sizes = s->w300 m->w780 l->w1280 o->original(default)
    def get_backdrop(self,img_size="o"):
        img_path = self.movies.get("backdrop_path")
        if not img_path:
            return
        return config['api']['base.url']+self.backdrop_sizes(img_size)+img_path

    def get_original_title(self):
        return self.movies["original_title"]

    def get_popularity(self):
        return self.movies["popularity"]

    def get_release_date(self):
        return self.movies["release_date"]

    def get_title(self):
        return self.movies["title"]

    # Sizes = s->w92 m->w185 l->w500 o->original(default)
    def get_poster(self,img_size="o"):
        img_path = self.movies.get("poster_path")
        if not img_path:
            return
        return config['api']['base.url']+self.poster_sizes(img_size)+img_path

    def get_trailers(self, language=None):
        return self.getJSON(config['urls']['movie.trailers'] % self.movie_id, language=language)

    def add_rating(self,value):
        if isinstance(value,float) or isinstance(value,int):
            if config["api"]["session.id"] == "":
                return "PROBLEM_AUTH"
            sess_id = config["api"]["session.id"]
            data = {"value":float(value)}
            req = requests.post(config['urls']['movie.add.rating'] % (self.movie_id,sess_id),data=data)
            res = simplejson.loads(bytes(req.content).decode())
            if res['status_message'] == "Success":
                return True
            else:
                return False
        return "ERROR"

class People(Core):
    def __init__(self, people_name, limit=False, language=None):
        self.limit = limit
        self.update_configuration()
        people_name = self.escape(people_name)
        self.people = self.getJSON(config['urls']['people.search'] % (people_name,str(1)), language=language)
        pages = self.people["total_pages"]
        if not self.limit:
            if int(pages) > 1:
                for i in range(2,int(pages)+1):
                    self.people["results"].extend(self.getJSON(config['urls']['people.search'] % (people_name,str(i)), language=language)["results"])

    def __iter__(self):
        for i in self.people["results"]:
            yield Person(i["id"])

    def total_results(self):
        return self.people["total_results"]

    def get_total_results(self):
        if self.limit:
            return len(self.movies["results"])
        return self.movies["total_results"]

    def iter_results(self):
        for i in self.people["results"]:
            yield i

class Person(Core):
    def __init__(self, person_id, language=None):
        self.person_id = person_id
        self.update_configuration()
        self.person = self.getJSON(config['urls']['person.info'] % self.person_id, language=language)

    def get_id(self):
        return self.person_id

    def is_adult(self):
        return self.person["adult"]

    def get_name(self):
        return self.person["name"]

    # Sizes = s->w45 m->w185 l->w632 o->original(default)
    def get_profile_image(self,img_size="o"):
        img_path = self.person.get("profile_path")
        if not img_path:
            return
        return config['api']['base.url']+self.profile_sizes(img_size)+img_path

    def get_biography(self):
        return self.person['biography']

    def get_birthday(self):
        return self.person['birthday']

    def get_deathday(self):
        return self.person['deathday']

    def get_place_of_birth(self):
        return self.person['place_of_birth']

    def get_homepage(self):
        return self.person['homepage']

    def get_also_known_as(self):
        return self.person['also_known_as']

    def get_image_aspect_ratio(self,image_index=0):
        return self.person["images"]['profiles'][image_index]['aspect_ratio']

    def get_image_height(self,image_index=0):
        return self.person["images"]['profiles'][image_index]['height']

    def get_image_width(self,image_index=0):
        return self.person["images"]['profiles'][image_index]['width']

    def get_image_iso_639_1(self,image_index=0):
        return self.person["images"]['profiles'][image_index]['iso_639_1']

    #Sizes = s->w92 m->w185 l->w500 o->original(default)
    def get_image(self,img_size="o",image_index=0):
        try:
            img_path = self.person["images"]['profiles'][image_index]['file_path']
        except KeyError:
            return
        return config['api']['base.url']+self.poster_sizes(img_size)+img_path

    def cast(self):
        for c in self.person["credits"]["cast"]:
            yield Cast(c)

    def crew(self):
        for c in self.person["credits"]["crew"]:
            yield Crew(c)


class Cast:
    def __init__(self,c):
        self.cast = c

    def get_id(self):
        return self.cast["id"]

    def get_character(self):
        return self.cast["character"]

    def get_original_title(self):
        return self.cast["original_title"]

    def get_title(self):
        return self.cast["title"]

    def get_release_date(self):
        return self.cast["release_date"]

    # Sizes = s->w92 m->w185 l->w500 o->original(default)
    def get_poster(self,img_size="o",person_index=0):
        img_path = self.cast.get("poster_path")
        if not img_path:
            return
        return config['api']['base.url']+Core().poster_sizes(img_size)+img_path

class Crew:
    def __init__(self,c):
        self.crew = c

    def get_id(self):
        return self.crew["id"]

    def get_department(self):
        return self.crew["department"]

    def get_job(self):
        return self.crew["job"]

    def get_original_title(self):
        return self.crew["original_title"]

    def get_title(self):
        return self.crew["title"]

    def get_release_date(self):
        return self.crew["release_date"]

    # Sizes = s->w92 m->w185 l->w500 o->original(default)
    def get_poster(self,img_size="o"):
        img_path = self.crew.get("poster_path")
        if not img_path:
            return
        return config['api']['base.url']+Core().poster_sizes(img_size)+img_path
