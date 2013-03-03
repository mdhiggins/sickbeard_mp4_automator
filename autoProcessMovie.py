import sys
import urllib
import os.path
import shutil
import ConfigParser
import time
import json 
from pprint import pprint 

class AuthURLOpener(urllib.FancyURLopener):
    def __init__(self, user, pw):
        self.username = user
        self.password = pw
        self.numTries = 0
        urllib.FancyURLopener.__init__(self)
    
    def prompt_user_passwd(self, host, realm):
        if self.numTries == 0:
            self.numTries = 1
            return (self.username, self.password)
        else:
            return ('', '')

    def openit(self, url):
        self.numTries = 0
        return urllib.FancyURLopener.open(self, url)


def process(dirName, nzbName=None, status=0):

    status = int(status)
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    print "Loading config from", configFilename
    
    if not os.path.isfile(configFilename):
        print "ERROR: You need an autoProcessMedia.cfg file - did you rename and edit the .sample?"
        sys.exit(-1)
    
    config.read(configFilename)
    
    host = config.get("CouchPotato", "host")
    port = config.get("CouchPotato", "port")
    username = config.get("CouchPotato", "username")
    password = config.get("CouchPotato", "password")
    apikey = config.get("CouchPotato", "apikey")
    delay = float(config.get("CouchPotato", "delay"))
    method = config.get("CouchPotato", "method")
    delete_failed = int(config.get("CouchPotato", "delete_failed"))

    try:
        ssl = int(config.get("CouchPotato", "ssl"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0
   
    try:
        web_root = config.get("CouchPotato", "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""

    myOpener = AuthURLOpener(username, password)

    nzbName1 = str(nzbName)

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"
    # don't delay when we are calling this script manually.    
    if  nzbName == "Manual Run":  
        delay = 0
        
    if status == 0:
        if method == "manage":
            command = "manage.update" 
        else:
            command = "renamer.scan" 

        url = protocol + host + ":" + port + web_root + "/api/" + apikey + "/" + command

        print "waiting for", str(delay), "seconds to allow CPS to process newly extracted files"

        time.sleep(delay)

        print "Opening URL:", url
    
        try:
            urlObj = myOpener.openit(url)
        except IOError, e:
            print "Unable to open URL: ", str(e)
            sys.exit(1)
    
        result = json.load(urlObj)
        print "CouchPotatoServer returned", result
        if result['success']:
            print command, "started on CouchPotatoServer for", nzbName1
        else:
            print "Error", command, "has NOT started on CouchPotatoServer for", nzbName1

    else:
        print "download of", nzbName1, "has failed."
        print "trying to re-cue the next highest ranked release"
        a=nzbName1.find('.cp(')+4
        b=nzbName1[a:].find(')')+a
        imdbid=nzbName1[a:b]
        #print imdbid

        url = protocol + host + ":" + port + web_root + "/api/" + apikey + "/movie.list"
        
        print "Opening URL:", url
    
        try:
            urlObj = myOpener.openit(url)
        except IOError, e:
            print "Unable to open URL: ", str(e)
            sys.exit(1)

        n=0
        result = json.load(urlObj)
        movieid = [item["id"] for item in result["movies"]]
        library = [item["library"] for item in result["movies"]]
        identifier = [item["identifier"] for item in library]
        for index in range(len(movieid)):
            if identifier[index] == imdbid:
                movid = str(movieid[index])
                print "found movie id", movid, "in database for release", nzbName1
                n = n + 1
                break

        if n == 0:
            print "cound not find a movie in the database for release", nzbName1
            print "please manually ignore this release and refresh the wanted movie"
            print "exiting postprocessing script"
            sys.exit(1)
        
        url = protocol + host + ":" + port + web_root + "/api/" + apikey + "/searcher.try_next/?id=" + movid
        
        print "Opening URL:", url
    
        try:
            urlObj = myOpener.openit(url)
        except IOError, e:
            print "Unable to open URL: ", str(e)
            sys.exit(1)
        
        result = urlObj.readlines()
        for line in result:
            print line
    
        print "movie", movid, "set to try the next best release on CouchPotatoServer"
        if delete_failed:
            print "Deleting failed files and folder", dirName
            shutil.rmtree(dirName)
