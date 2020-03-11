import sys
try:
    from urllib.request import FancyURLopener
except ImportError:
    from urllib import FancyURLopener
import os.path
import shutil
import time
import json
import logging
import requests


class AuthURLOpener(FancyURLopener):
    def __init__(self, user, pw):
        self.username = user
        self.password = pw
        self.numTries = 0
        FancyURLopener.__init__(self)

    def prompt_user_passwd(self, host, realm):
        if self.numTries == 0:
            self.numTries = 1
            return (self.username, self.password)
        else:
            return ('', '')

    def openit(self, url):
        self.numTries = 0
        return FancyURLopener.open(self, url)


def process(dirName, settings, nzbName=None, status=0, logger=None):
    log = logger or logging.getLogger(__name__)

    status = int(status)

    host = settings.CP['host']
    port = settings.CP['port']
    username = settings.CP['username']
    password = settings.CP['password']
    apikey = settings.CP['apikey']
    delay = settings.CP['delay']
    method = settings.CP['method']
    delete_failed = settings.CP['delete_failed']
    protocol = "https://" if settings.CP['ssl'] else "http://"
    webroot = settings.CP['webroot']

    if webroot != "" and not webroot.startswith("/"):
        webroot = "/" + webroot

    myOpener = AuthURLOpener(username, password)
    nzbName1 = str(nzbName)

    # Don't delay when we are calling this script manually.
    if nzbName == "Manual Run":
        delay = 0

    log.debug("Host: %s." % host)
    log.debug("Port: %s." % port)
    log.debug("Username: %s." % username)
    log.debug("Password: %s." % password)
    log.debug("APIKey: %s." % apikey)
    log.debug("Delay: %s." % delay)
    log.debug("Method: %s." % method)
    log.debug("Delete Failed: %s." % delete_failed)
    log.debug("Protocol: %s." % protocol)
    log.debug("Web Root: %s." % webroot)

    if status == 0:
        if method == "manage":
            command = "manage.update"
        else:
            command = "renamer.scan"

        url = protocol + host + ":" + str(port) + webroot + "/api/" + apikey + "/" + command

        params = {'media_folder': dirName, 'downloader': 'manual'}

        log.info("Waiting for %s seconds to allow CPS to process newly extracted files." % str(delay))

        time.sleep(delay)

        log.info("Opening URL: %s." % url)

        r = requests.get(url, params=params)

        rstate = r.json()

        log.info("CouchPotatoServer returned %s." % rstate)
        if rstate['success']:
            log.info("%s started on CouchPotatoServer for %s." % (command, nzbName1))
        else:
            log.error("%s has NOT started on CouchPotatoServer for %s." % (command, nzbName1))

    else:
        log.info("Download of %s has failed." % nzbName1)
        log.info("Trying to re-cue the next highest ranked release.")
        try:
            a = nzbName1.find('.cp(') + 4
            b = nzbName1[a:].find(')') + a
            imdbid = nzbName1[a:b]

            log.debug("Attempt to determine IMDBID resulted in '%s'." % imdbid)
        except:
            log.exception("Unable to determine release IMDB ID for requeueing.")
            sys.exit()

        url = protocol + host + ":" + str(port) + webroot + "/api/" + apikey + "/movie.list"
        log.info("Opening URL: %s." % url)

        try:
            urlObj = myOpener.openit(url)
        except IOError:
            log.exception("Unable to open URL.")
            sys.exit(1)

        n = 0
        result = json.load(urlObj)
        movieid = [item["info"]["imdb"] for item in result["movies"]]

        log.debug("Movie ID: %s." % movieid)

        for index in range(len(movieid)):
            if movieid[index] == imdbid:
                movid = str(movieid[index])
                log.info("Found movie id %s in database for release %s." % (movid, nzbName1))
                n = n + 1
                break

        if n == 0:
            log.error("Cound not find a movie in the database for release %s." % nzbName1)
            log.error("Please manually ignore this release and refresh the wanted movie.")
            log.error("Exiting postprocessing script")
            sys.exit(1)

        url = protocol + host + ":" + str(port) + webroot + "/api/" + apikey + "/movie.searcher.try_next/?media_id=" + movid
        log.info("Opening URL: %s." % url)

        try:
            urlObj = myOpener.openit(url)
        except IOError:
            log.exception("Unable to open URL.")
            sys.exit(1)

        result = urlObj.readlines()
        for line in result:
            log.info(line)

        log.info("Movie %s set to try the next best release on CouchPotatoServer." % movid)
        if delete_failed:
            log.error("Deleting failed files and folder %s." % dirName)
            shutil.rmtree(dirName)
