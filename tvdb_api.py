#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:Creative Commons GNU GPL v2 
# (http://creativecommons.org/licenses/GPL/2.0/)

"""
tvdb_api.py
Simple-to-use Python interface to The TVDB's API (www.thetvdb.com)

Example usage:

>>> from tvdb_api import tvdb
>>> db = tvdb()
>>> db['Lost'][4][11]['name']
'Cabin Fever'
"""
__author__ = "dbr/Ben"
__version__ = "0.2"

class _Ddict(dict):
    """Lazy-dict, automatically creates multidimensional dicts
    by having __getitem__ create sub-dicts automatically"""
    def __init__(self, default=None):
        dict.__init__(self)
        self.default = default
    #end __init__

    def __getitem__(self, key):
        if not self.has_key(key):
            self[key] = self.__class__(self.default) # Create sub-instance
        return dict.__getitem__(self, key)
    #end __getitem__
#end _Ddict

class Cache:
    """
    Simple caching URL opener. Acts like:
    import urllib
    return urllib.urlopen("http://example.com").read()
    
    Caches complete files to temp directory, 
    
    >>> ca = Cache()
    >>> ca.loadUrl("http://example.com")
    <html><body>page!</body></html>
    """
    import os
    import time
    import tempfile
    import urllib
    try:
        import sha1 as hasher
    except ImportError:
        import md5 as hasher
    
    def __init__(self, max_age=21600, prefix="tvdb_api"):
        self.prefix = prefix
        self.max_age = max_age
        
        tmp = self.tempfile.gettempdir()
        tmppath = self.os.path.join(tmp, prefix)
        if not self.os.path.isdir(tmppath):
            self.os.mkdir(tmppath)
        self.tmp = tmppath
    #end __init__
    
    def getCachePath(self, url):
        """
        Calculates the cache path (/temp_directory/hash_of_URL)
        """
        cache_name = self.hasher.new(url).hexdigest()
        cache_path = self.os.path.join(self.tmp, cache_name)
        return cache_path
    #end getUrl
    
    def checkCache(self, url):
        """
        Takes a URL, checks if a cache exists for it.
        If so, returns path, if not, returns False
        """
        path = self.getCachePath(url)
        if self.os.path.isfile(path):
            cache_modified_time = self.os.stat(path).st_mtime
            time_now = self.time.time()
            if cache_modified_time < time_now - self.max_age:
                # Cache is old
                return False
            else:
                return path
        else:
            return False
    #end checkCache

    def loadUrl(self, url):
        """
        Takes a URL, returns the contents of the URL, and does the caching.
        """
        cacheExists = self.checkCache(url)
        if cacheExists:
            cache_file = open(cacheExists)
            dat = cache_file.read()
            cache_file.close()
            return dat
        else:
            path = self.getCachePath(url)
            dat = self.urllib.urlopen(url).read()
            target_socket = open(path, "w+")
            target_socket.write(dat)
            target_socket.close()
            return dat
        #end if cacheExists
    #end loadUrl
#end Cache


# Custom exceptions
class tvdb_error(Exception):
    """
    An error with www.thetvdb.com (Cannot connect, for example)
    """
    pass
class tvdb_userabort(Exception):
    """
    User aborted the interactive selection (via
    the q command, ^c etc)
    """
    pass
class tvdb_shownotfound(Exception):
    """
    Show cannot be found on www.thetvdb.com (non-existant show)
    """
    pass
class tvdb_seasonnotfound(Exception):
    """
    Season cannot be found on www.thetvdb.com
    """
    pass
class tvdb_episodenotfound(Exception):
    """
    Episode cannot be found on www.thetvdb.com
    """
    pass
class tvdb_attributenotfound(Exception):
    """
    Raised if an episode does not have the requested 
    attribute (such as a episode name)
    """
    pass


class ShowContainer:
    def __init__(self):
        self.shows = {}
    def has_key(self, key):
        return dict.has_key(self.shows, key)
    def __setitem__(self, showid, value):
        dict.__setitem__(self.shows, showid, value)
    def __getitem__(self, showid):
        if not dict.has_key(self.shows, showid):
            raise tvdb_shownotfound
        else:
            return dict.__getitem__(self.shows, showid)
class Show:
    def __init__(self):
        self.seasons = {}
        self.data = {}
    def has_key(self, key):
        return dict.has_key(self.seasons, key)
    def __setitem__(self, season_number, value):
        dict.__setitem__(self.seasons, season_number, value)
    def __getitem__(self, season_numer):
        if not dict.has_key(self.seasons, season_numer):
            # Season number doesn't exist
            if dict.has_key(self.data, season_numer):
                # check if it's a bit of data
                return  dict.__getitem__(self.data, season_numer)
            else:
                # Nope, it doesn't exist
                raise tvdb_seasonnotfound
        else:
            return dict.__getitem__(self.seasons, season_numer)
class Season:
    def __init__(self):
        self.episodes = {}
    def has_key(self, key):
        return dict.has_key(self.episodes, key)
    def __setitem__(self, episode_number, value):
        dict.__setitem__(self.episodes, episode_number, value)
    def __getitem__(self, episode_number):
        if not dict.has_key(self.episodes, episode_number):
            print "episodes does not have key", episode_number
            raise tvdb_episodenotfound
        else:
            return dict.__getitem__(self.episodes, episode_number)
class Episode:
    def __init__(self):
        self.data = {}
    def __getitem__(self, key):
        if not dict.has_key(self.data, key):
            raise tvdb_attributenotfound
        else:
            return dict.__getitem__(self.data, key)
    def __setitem__(self, key, value):
        dict.__setitem__(self.data, key, value)


class Tvdb:
    """
    Create easy-to-use interface to name of season/episode name
    >>> i = Tvdb()
    >>> i['showname']['1']['24']['name']
    'Last Episode'
    """
    from BeautifulSoup import BeautifulStoneSoup
    import random
    
    def __init__(self, interactive=False, debug=False):
        self.shows = ShowContainer() # Holds all Show classes
        self.corrections = {} # Holds show-name to show_id mapping
        
        self.config = {}
        
        self.config['apikey'] = "0629B785CE550C8D" # thetvdb.com API key
        
        self.config['debug_enabled'] = debug # show debugging messages
        self.config['debug_tofile'] = False
        self.config['debug_filename'] = "tvdb.log"
        self.config['debug_path'] = '.'
        
        self.config['interactive'] = interactive # prompt for correct series?
        
        self.cache = Cache(prefix="tvdb_api") # Caches retreived URLs in tmp dir
        self.log = self._initLogger() # Setups the logger (self.log.debug() etc)
        
        # The following url_ configs are based of the
        # http://thetvdb.com/wiki/index.php/Programmers_API
        self.config['url_mirror'] = "http://www.thetvdb.com/api/%(apikey)s/mirrors.xml" % self.config
        self.mirrors = self._getMirrors()
        
        self.config['random_mirror'] = self.random.choice(self.mirrors)
        
        self.config['url_getSeries'] = "%(random_mirror)s/api/GetSeries.php?seriesname=%%s" % self.config
        self.config['url_epInfo'] = "%(random_mirror)s/api/%(apikey)s/series/%%s/all/" % self.config
    #end __init__
    
    def _initLogger(self):
        """
        Setups a logger using the logging module, returns a log object
        """
        import os, logging, sys
        logdir = os.path.expanduser( self.config['debug_path'] )
        logpath = os.path.join(logdir, self.config['debug_filename'])
        
        logger = logging.getLogger("tvdb")
        formatter = logging.Formatter('%(asctime)s) %(levelname)s %(message)s')
        
        if self.config['debug_tofile']:
            hdlr = logging.FileHandler(logpath)
        else:
            hdlr = logging.StreamHandler(sys.stdout)
        #end if debug_tofile
        
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)
        
        if self.config['debug_enabled']:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        return logger
    #end initLogger
    
    def _getsoupsrc(self, url):
        """
        Helper to get a URL, turn it into 
        a BeautifulStoneSoup instance (for XML parsing)
        """
        self.log.debug('Retriving URL %s' % (url.replace(" ", "+")))
        
        url = url.replace(" ", "+")
        try:
            src = self.cache.loadUrl(url)
        except IOError, errormsg:
            raise tvdb_error("Could not connect to server: %s\n" % (errormsg))
        #end try
        soup = self.BeautifulStoneSoup(src)
        return soup
    #end _getsoupsrc
    
    def _setItem(self, sid, seas, ep, attrib, value):
        """
        Creates a new episode, creating Show(), Season() and
        Episode()s as required. Called by _getEps to populute
        
        Since the nice-to-use tvdb[1][24]['name] interface
        makes it impossible to do tvdb[1][24]['name] = "name"
        and still be capable of checking if an episode exists
        so we can raise tvdb_shownotfound, we have a slightly
        less pretty method of setting items.. but since the API
        is supposed to be read-only, this is the best way to
        do it!
        The problem is that calling tvdb[1][24]['name'] = "name"
        calls __getitem__ on tvdb[1], there is no way to check if
        tvdb.__dict__ should have a key "1" before we auto-create it
        """
        if not self.shows.has_key(sid):
            self.shows[sid] = Show()
        if not self.shows[sid].has_key(seas):
            self.shows[sid][seas] = Season()
        if not self.shows[sid][seas].has_key(ep):
            self.shows[sid][seas][ep] = Episode()
        self.shows[sid][seas][ep][attrib] = value
    #end _set_item
    
    def _setShowData(self, sid, key, value):
        if not self.shows.has_key(sid):
            self.shows[sid] = Show()
        self.shows[sid].data.__setitem__(key, value)
    
    def _getMirrors(self):
        """
        Gets a list of mirrors from the API
        """
        mirrorSoup = self._getsoupsrc( self.config['url_mirror'] )
        mirrors = []
        for mirror in mirrorSoup.findAll('mirror'):
            self.log.debug('Found mirror %s' % (mirror))
            
            mirrors.append(
                mirror.find('mirrorpath').contents[0]
            )
        #end for mirror
        self.log.debug('Found total of %s mirrors' % (len(mirrors)))
        return mirrors
    #end _getMirrors

    def _cleanName(self, name):
        """
        Cleans up showname returned by TheTVDB.com
        
        Issues corrected:
        - Returns &amp; instead of &, since &s in filenames
        are bad, replace &amp; with "and"
        """
        name = name.replace("&amp;", "and")
        return name
    #end _cleanName
    
    def _getSeries(self, series):
        """
        This searches TheTVDB.com for the series name,
        and either interactivly selects the correct show,
        or returns the first result.
        """
        seriesSoup = self._getsoupsrc( self.config['url_getSeries'] % (series) )
        allSeries = []
        for series in seriesSoup.findAll('series'):
            cur_name = series.find('seriesname').contents[0]
            cur_name = self._cleanName(cur_name)
            cur_sid = series.find('id').contents[0]
            self.log.debug('Found series %s (id: %s)' % (cur_name, cur_sid))
            allSeries.append( {'sid':cur_sid, 'name':cur_name} )
        #end for series
        
        if len(allSeries) == 0:
            self.log.debug('Series result returned zero')
            raise tvdb_shownotfound("Show-name search returned zero results (cannot find show on TVDB)")
        
        if not self.config['interactive']:
            self.log.debug('Auto-selecting first search result')
            return allSeries[0]
        else:
            self.log.debug('Interactivily selecting show')
            print "TVDB Search Results:"
            for i in range(len(allSeries[:6])): # list first 6 search results
                i_show = i + 1 # Start at more human readable number 1 (not 0)
                self.log.debug('Showing allSeries[%s] = %s)' % (i_show, allSeries[i]))
                print "%s -> %s (tvdb id: %s)" % (
                    i_show,
                    allSeries[i]['name'].encode("UTF-8","ignore"),
                    allSeries[i]['sid'].encode("UTF-8","ignore")
                )
            
            valid_input = False
            while not valid_input:
                try:
                    print "Enter choice (first number, ? for help):"
                    ans = raw_input()
                except KeyboardInterrupt:
                    raise tvdb_userabort("User aborted (^c keyboard interupt)")
            
                self.log.debug('Got choice of: %s' % (ans))
                try:
                    selected_id = int(ans) - 1 # The human entered 1 as first result, not zero
                    self.log.debug('Trying to return ID: %d' % (selected_id))
                    return allSeries[ selected_id ]
                except ValueError: # Input was not number
                    if ans == "q":
                        self.log.debug('Got quit command (q)')
                        raise tvdb_userabort("User aborted ('q' quit command)")
                    elif ans == "?":
                        print "## Help"
                        print "# Enter the number that corresponds to the correct show."
                        print "# ? - this help"
                        print "# q - abort tvnamer"
                    else:
                        self.log.debug('Unknown keypress %s' % (ans))
                #end try
            #end while not valid_input
    #end _getSeries

    def _getEps(self, sid):
        """
        Takes a series ID, gets the epInfo URL and parses the TVDB
        XML file into the shows dict in layout:
        shows[series_id][season_number][episode_number]
        """
        self.log.debug('Getting all episodes of %s' % (sid))
        epsSoup = self._getsoupsrc( self.config['url_epInfo']% (sid) )
        for ep in epsSoup.findAll('episode'):
            ep_no = int( ep.find('episodenumber').contents[0] )
            seas_no = int( ep.find('seasonnumber').contents[0] )
            if len( ep.find('episodename').contents ) == 0:
                self.log.debug('Could not find episode name for seas:%s ep:%s' % (seas_no, ep_no))
                ep_name = None
            else:
                ep_name = str( ep.find('episodename').contents[0] )
            self._setItem(sid, seas_no, ep_no, 'name', ep_name)
        #end for ep
    #end _geEps
    
    def _nameToSid(self, name):
        """
        Takes show name, returns the correct series ID (if the show has
        already been grabbed), or grabs all episodes and returns 
        the correct SID.
        """
        if self.corrections.has_key(name):
            self.log.debug('Correcting %s to %s' % (name, self.corrections[name]) )
            sid = self.corrections[name]
        else:
            self.log.debug('Getting show %s' % (name))
            selected_series = self._getSeries( name )
            sname, sid = selected_series['name'], selected_series['sid']
            self.log.debug('Got %s, sid %s' % (sname, sid) )
            
            self._setShowData(sid, 'showname', sname)
            self.corrections[name] = sid
            self._getEps( sid )
        #end if self.corrections.has_key
        return sid
    #end _nameToSid

    def __getitem__(self, key):
        """
        Handles tvdb_instance['showname'] calls.
        The dict index should be the show id
        """
        key = key.lower() # make key lower case
        sid = self._nameToSid(key)
        self.log.debug('Got series id %s' % (sid))
        return self.shows[sid]
    #end __getitem__
    
    def __setitem__(self, key, value):
        self.log.debug('Setting %s = %s' % (key, value))
        self.shows[key] = value
    #end __getitem__
    
    def __str__(self):
        return str(self.shows)
    #end __str__
#end Tvdb

import unittest
class test_tvdb(unittest.TestCase):
    def setUp(self):
        self.t = Tvdb()
    
    def test_different_case(self):
        """
        Checks the auto-correction of show names is working.
        It should correct the weirdly capitalised 'sCruBs' to 'Scrubs'
        """
        self.assertEquals(self.t['scrubs'][1][4]['name'], 'My Old Lady')
        self.assertEquals(self.t['sCruBs']['showname'], 'Scrubs')
    
    def test_spaces(self):
        self.assertEquals(self.t['My Name Is Earl']['showname'], 'My Name Is Earl')
        self.assertEquals(self.t['My Name Is Earl'][1][4]['name'], 'Faked His Own Death')
    
    def test_numeric(self):
        self.assertEquals(self.t['24'][2][20]['name'], 'Day 2: 3:00 A.M.-4:00 A.M.')
        self.assertEquals(self.t['24']['showname'], '24')
    
    def test_seasonnotfound(self):
        """
        Using CNNNN, as it is cancelled so it's rather unlikely 
        they'll make another 8 seasons..
        """
        self.assertRaises(tvdb_seasonnotfound, lambda:self.t['CNNNN'][10][1])
    
    def test_shownotfound(self):
        """
        Hopefully no-one creates a show called "the fake show thingy"..
        """
        self.assertRaises(tvdb_shownotfound, lambda:self.t['the fake show thingy'])
        
    def test_episodenamenotfound(self):
        """
        Check it raises tvdb_attributenotfound if an episode name is not found.
        CNNNN is a fake news program, so episodes don't have names, and the
        show has been moved to "Chaser Constant News Network" so it wont 
        be updated ever (to have the episode name be the air-date)
        """
        self.assertRaises(tvdb_attributenotfound, lambda:self.t['CNNNN'][1][6]['afakeattributething'])
#end test_tvnamer

    
def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(test_tvdb)
    unittest.TextTestRunner(verbosity=2).run(suite)

def simple_example():
    """
    Simple example of using tvdb_api - it just 
    grabs an episode name interactivly.
    """
    db = Tvdb(interactive=True, debug=True)
    print db['Lost']['showname']
    print db['Lost'][1][4]['name']

def main():
    """
    Parses command line options, either runs
    tests or a simple example using Tvdb()
    """
    from optparse import OptionParser
    
    parser = OptionParser(usage="%prog [options]")
    parser.add_option(  "-t", "--tests", action="store_true", default=False, dest="dotests",
                        help="Run unittests (mostly useful for development)")

    opts, args = parser.parse_args()
    
    if opts.dotests:
        run_tests()
    else:
        simple_example()


if __name__ == '__main__':
    main()