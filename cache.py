"""
urllib2 caching handler
Modified from http://code.activestate.com/recipes/491261/
"""

import os
import httplib
import urllib2
import StringIO
from hashlib import md5

def calculate_cache_path(cache_location, url):
    """Checks if cache_location/hash_of_url.headers an .body exist
    """
    thumb = md5(url).hexdigest()
    header = os.path.join(cache_location, thumb + ".headers")
    body = os.path.join(cache_location, thumb + ".body")
    return header, body

def existsInCache(cache_location, url):
    """Returns if header AND body cache file exist"""
    hpath, bpath = calculate_cache_path(cache_location, url)
    return os.path.exists(hpath) and os.path.exists(bpath)

def store_in_cache(cache_location, url, response):
    """Tries to store response in cache"""
    hpath, bpath = calculate_cache_path(cache_location, url)
    try:
        outf = open(hpath, "w")
        headers = str(response.info())
        outf.write(headers)
        outf.close()

        outf = open(bpath, "w")
        outf.write(response.read())
        outf.close()
    except IOError:
        pass

class CacheHandler(urllib2.BaseHandler):
    """Stores responses in a persistant on-disk cache.

    If a subsequent GET request is made for the same URL, the stored
    response is returned, saving time, resources and bandwith
    """
    def __init__(self, cache_location):
        """The location of the cache directory"""
        self.cache_location = cache_location
        if not os.path.exists(self.cache_location):
            os.mkdir(self.cache_location)

    def default_open(self, request):
        if ((request.get_method() == "GET") and
            (existsInCache(self.cache_location, request.get_full_url()))):
            return CachedResponse(
                self.cache_location,
                request.get_full_url(),
                set_cache_header=True
            )
        else:
            return None # let the next handler try to handle the request

    def http_response(self, request, response):
        if request.get_method() == "GET":
            if 'x-cache' not in response.info():
                store_in_cache(
                    self.cache_location,
                    request.get_full_url(),
                    response
                )
                set_cache_header = False
            else:
                set_cache_header = True
            #end if x-cahce in response
            return CachedResponse(
                self.cache_location,
                request.get_full_url(),
                set_cache_header=set_cache_header
            )
        else:
            return response

class CachedResponse(StringIO.StringIO):
    """An urllib2.response-like object for cached responses.

    To determine wheter a response is cached or coming directly from
    the network, check the x-cache header rather than the object type.
    """
    def __init__(self, cache_location, url, set_cache_header=True):
        self.cache_location = cache_location
        hpath, bpath = calculate_cache_path(cache_location, url)

        StringIO.StringIO.__init__(self, file(bpath).read)

        self.url     = url
        self.code    = 200
        self.msg     = "OK"
        headerbuf = file(hpath).read()
        if set_cache_header:
            headerbuf += "x-cache: %s\r\n" % (bpath)
        self.headers = httplib.HTTPMessage(StringIO.StringIO(headerbuf))

    def info(self):
        return self.headers
    def geturl(self):
        return self.url
