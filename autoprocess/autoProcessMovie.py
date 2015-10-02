import sys
import urllib
import os.path
import shutil
import time
import json
import logging


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


def process(dirName, settings, nzbName=None, status=0, logger=None):

    # Setup logging
    if logger:
        log = logger
    else:
        log = logging.getLogger(__name__)

    status = int(status)

    host = settings.CP['host']
    port = settings.CP['port']
    username = settings.CP['username']
    password = settings.CP['password']
    apikey = settings.CP['apikey']
    delay = settings.CP['delay']
    method = settings.CP['method']
    delete_failed = settings.CP['delete_failed']
    protocol = settings.CP['protocol']
    web_root = settings.CP['web_root']

    if web_root != "" and not web_root.startswith("/"):
        web_root = "/" + web_root

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
    log.debug("Web Root: %s." % web_root)

    if status == 0:
        if method == "manage":
            command = "manage.update"
        else:
            command = "renamer.scan"

        url = protocol + host + ":" + port + web_root + "/api/" + apikey + "/" + command

        log.info("Waiting for %s seconds to allow CPS to process newly extracted files." % str(delay))

        time.sleep(delay)

        log.info("Opening URL: %s." % url)

        try:
            urlObj = myOpener.openit(url)
        except IOError, e:
            log.exception("Unable to open URL.")
            sys.exit(1)

        result = json.load(urlObj)
        log.info("CouchPotatoServer returned %s." % result)
        if result['success']:
            log.info("%s started on CouchPotatoServer for %s." % (command, nzbName1))
        else:
            log.error("%s has NOT started on CouchPotatoServer for %s." % (command, nzbName1))

    else:
        log.info("Download of %s has failed." % nzbName1)
        log.info("Trying to re-cue the next highest ranked release.")
        a = nzbName1.find('.cp(') + 4
        b = nzbName1[a:].find(')') + a
        imdbid = nzbName1[a:b]

        log.debug("Attempt to determine IMDBID resulted in '%s'." % imdbid)

        url = protocol + host + ":" + port + web_root + "/api/" + apikey + "/movie.list"
        log.info("Opening URL: %s." % url)

        try:
            urlObj = myOpener.openit(url)
        except IOError, e:
            log.exception("Unable to open URL.")
            sys.exit(1)

        n = 0
        result = json.load(urlObj)
        movieid = [item["id"] for item in result["movies"]]
        library = [item["library"] for item in result["movies"]]
        identifier = [item["identifier"] for item in library]

        log.debug("Movie ID: %s." % movieid)
        log.debug("Library: %s." % library)
        log.debug("Identifier: %s" % identifier)

        for index in range(len(movieid)):
            if identifier[index] == imdbid:
                movid = str(movieid[index])
                log.info("Found movie id %s in database for release %s." % (movid, nzbName1))
                n = n + 1
                break

        if n == 0:
            log.error("Cound not find a movie in the database for release %s." % nzbName1)
            log.error("Please manually ignore this release and refresh the wanted movie.")
            log.error("Exiting postprocessing script")
            sys.exit(1)

        url = protocol + host + ":" + port + web_root + "/api/" + apikey + "/searcher.try_next/?id=" + movid
        log.info("Opening URL: %s." % url)

        try:
            urlObj = myOpener.openit(url)
        except IOError, e:
            log.exception("Unable to open URL.")
            sys.exit(1)

        result = urlObj.readlines()
        for line in result:
            log.info(line)

        log.info("Movie %s set to try the next best release on CouchPotatoServer." % movid)
        if delete_failed:
            log.error("Deleting failed files and folder %s." % dirName)
            shutil.rmtree(dirName)
