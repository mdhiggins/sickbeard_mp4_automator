#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)

"""
urllib2 caching handler
Modified from http://code.activestate.com/recipes/491261/
"""
from __future__ import with_statement

__author__ = "dbr/Ben"
__version__ = "1.2.1"

import os
import time
import errno
import httplib
import urllib2
import StringIO
from hashlib import md5
from threading import RLock

cache_lock = RLock()

class FileLockException(Exception):
    pass

class FileLock(object):
    """ A file locking mechanism that has context-manager support so
        you can use it in a with statement. This should be relatively cross
        compatible as it doesn't rely on msvcrt or fcntl for the locking.

        Modified from http://www.evanfosmark.com/2009/01/cross-platform-file-locking-support-in-python/
    """

    def __init__(self, file_name, timeout=10, delay=.05, lock_folder = False):
        """ Prepare the file locker. Specify the file to lock and optionally
            the maximum timeout and the delay between each attempt to lock.
        """
        self.is_locked = False
        if lock_folder:
            enclosing_dir, dirname = os.path.split(os.path.split(file_name)[0])
            self.lockfile = os.path.join(enclosing_dir, "%s.lock" % dirname)
        else:
            dirname = os.path.split(os.path.abspath(file_name))[0]
            print file_name
            self.lockfile = os.path.join(dirname, "%s.lock" % file_name)

        self.file_name = file_name
        self.timeout = timeout
        self.delay = delay

    def acquire(self):
        """ Acquire the lock, if possible. If the lock is in use, it check again
            every `wait` seconds. It does this until it either gets the lock or
            exceeds `timeout` number of seconds, in which case it throws
            an exception.
        """
        start_time = time.time()
        while True:
            try:
                self.fd = os.open(self.lockfile, os.O_CREAT|os.O_EXCL|os.O_RDWR)
                break;
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise e
                if (time.time() - start_time) >= self.timeout:
                    raise FileLockException("Timeout occured.")
                time.sleep(self.delay)
        self.is_locked = True

    def release(self):
        """ Get rid of the lock by deleting the lockfile.
            When working in a `with` statement, this gets automatically
            called at the end.
        """
        if self.is_locked:
            os.close(self.fd)
            os.unlink(self.lockfile)
            self.is_locked = False

    def __enter__(self):
        """ Activated when used in the with statement.
            Should automatically acquire a lock to be used in the with block.
        """
        if not self.is_locked:
            self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        """ Activated at the end of the with statement.
            It automatically releases the lock if it isn't locked.
        """
        if self.is_locked:
            self.release()

    def __del__(self):
        """ Make sure that the FileLock instance doesn't leave a lockfile
            lying around.
        """
        self.release()

def locked_function(origfunc):
    """Decorator to execute function under lock"""
    def wrapped(*args, **kwargs):
        cache_lock.acquire()
        try:
            return origfunc(*args, **kwargs)
        finally:
            cache_lock.release()
    return wrapped

def calculate_cache_path(cache_location, url):
    """Checks if [cache_location]/[hash_of_url].headers and .body exist
    """
    thumb = md5(url).hexdigest()
    header = os.path.join(cache_location, thumb + ".headers")
    body = os.path.join(cache_location, thumb + ".body")
    return header, body

def check_cache_time(path, max_age):
    """Checks if a file has been created/modified in the [last max_age] seconds.
    False means the file is too old (or doesn't exist), True means it is
    up-to-date and valid"""
    if not os.path.isfile(path):
        return False
    cache_modified_time = os.stat(path).st_mtime
    time_now = time.time()
    if cache_modified_time < time_now - max_age:
        # Cache is old
        return False
    else:
        return True

@locked_function
def exists_in_cache(cache_location, url, max_age):
    """Returns if header AND body cache file exist (and are up-to-date)"""
    hpath, bpath = calculate_cache_path(cache_location, url)
    if os.path.exists(hpath) and os.path.exists(bpath):
        return(
            check_cache_time(hpath, max_age)
            and check_cache_time(bpath, max_age)
        )
    else:
        # File does not exist
        return False

@locked_function
def store_in_cache(cache_location, url, response):
    """Tries to store response in cache."""
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
        return True
    else:
        return False

class CacheHandler(urllib2.BaseHandler):
    """Stores responses in a persistant on-disk cache.

    If a subsequent GET request is made for the same URL, the stored
    response is returned, saving time, resources and bandwidth
    """
    @locked_function
    def __init__(self, cache_location, max_age = 21600):
        """The location of the cache directory"""
        self.max_age = max_age
        self.cache_location = cache_location
        with FileLock(self.cache_location, lock_folder = True):
            if not os.path.exists(self.cache_location):
                os.mkdir(self.cache_location)

    def default_open(self, request):
        """Handles GET requests, if the response is cached it returns it
        """
        if request.get_method() is not "GET":
            return None # let the next handler try to handle the request

        if exists_in_cache(
            self.cache_location, request.get_full_url(), self.max_age
        ):
            return CachedResponse(
                self.cache_location,
                request.get_full_url(),
                set_cache_header = True
            )
        else:
            return None

    def http_response(self, request, response):
        """Gets a HTTP response, if it was a GET request and the status code
        starts with 2 (200 OK etc) it caches it and returns a CachedResponse
        """
        if (request.get_method() == "GET"
            and str(response.code).startswith("2")
        ):
            if 'x-local-cache' not in response.info():
                # Response is not cached
                set_cache_header = store_in_cache(
                    self.cache_location,
                    request.get_full_url(),
                    response
                )
            else:
                set_cache_header = True
            #end if x-cache in response

            return CachedResponse(
                self.cache_location,
                request.get_full_url(),
                set_cache_header = set_cache_header
            )
        else:
            return response

class CachedResponse(StringIO.StringIO):
    """An urllib2.response-like object for cached responses.

    To determine if a response is cached or coming directly from
    the network, check the x-local-cache header rather than the object type.
    """

    @locked_function
    def __init__(self, cache_location, url, set_cache_header=True):
        self.cache_location = cache_location
        hpath, bpath = calculate_cache_path(cache_location, url)

        StringIO.StringIO.__init__(self, file(bpath).read())

        self.url     = url
        self.code    = 200
        self.msg     = "OK"
        headerbuf = file(hpath).read()
        if set_cache_header:
            headerbuf += "x-local-cache: %s\r\n" % (bpath)
        self.headers = httplib.HTTPMessage(StringIO.StringIO(headerbuf))

    def info(self):
        """Returns headers
        """
        return self.headers

    def geturl(self):
        """Returns original URL
        """
        return self.url

    @locked_function
    def recache(self):
        new_request = urllib2.urlopen(self.url)
        set_cache_header = store_in_cache(
            self.cache_location,
            new_request.url,
            new_request
        )
        CachedResponse.__init__(self, self.cache_location, self.url, True)


if __name__ == "__main__":
    def main():
        """Quick test/example of CacheHandler"""
        opener = urllib2.build_opener(CacheHandler("/tmp/"))
        response = opener.open("http://google.com")
        print response.headers
        print "Response:", response.read()

        response.recache()
        print response.headers
        print "After recache:", response.read()

        # Test usage in threads
        from threading import Thread
        class CacheThreadTest(Thread):
            lastdata = None
            def run(self):
                req = opener.open("http://google.com")
                newdata = req.read()
                if self.lastdata is None:
                    self.lastdata = newdata
                assert self.lastdata == newdata, "Data was not consistent, uhoh"
                req.recache()
        threads = [CacheThreadTest() for x in range(50)]
        print "Starting threads"
        [t.start() for t in threads]
        print "..done"
        print "Joining threads"
        [t.join() for t in threads]
        print "..done"
    main()
