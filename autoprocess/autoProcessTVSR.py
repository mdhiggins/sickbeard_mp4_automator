#!/usr/bin/env python

#
# This file is adapted from the autoProcessTV file included with SickRage.
#

from __future__ import with_statement

import os.path
import sys
import logging

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), 'lib')))

def processEpisode(dir_to_process, settings, org_NZB_name=None, status=None):

    log = logging.getLogger(__name__)

    try:
        import requests
    except ImportError:
        log.exception("You need to install python requests library.")
        sys.exit(1)

    # Try importing Python 2 modules using new names
    try:
        import urllib2
        from urllib import urlencode
    # On error import Python 3 modules
    except ImportError:
        import urllib.request as urllib2
        from urllib.parse import urlencode

    host = settings.Sickrage['host']
    port = settings.Sickrage['port']
    username = settings.Sickrage['user']
    password = settings.Sickrage['pass']

    try:
        ssl = int(settings.Sickrage['ssl'])
    except:
        ssl = 0

    try:
        web_root = settings.Sickrage['web_root']
        if not web_root.startswith("/"):
            web_root = "/" + web_root
        if not web_root.endswith("/"):
            web_root = web_root + "/"
    except:
        web_root = ""

    params = {}

    params['quiet'] = 1

    params['dir'] = dir_to_process
    if org_NZB_name != None:
        params['nzbName'] = org_NZB_name

    if status != None:
        params['failed'] = status

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    url = protocol + host + ":" + port + web_root + "home/postprocess/processEpisode"
    login_url = protocol + host + ":" + port + web_root + "login"

    log.debug('Host: %s.' % host)
    log.debug('Port: %s.' % port)
    log.debug('Username: %s.' % username)
    log.debug('Password: %s.' % password)
    log.debug('Protocol: %s.' % protocol)
    log.debug('Web Root: %s.' % web_root)
    log.debug('URL: %s.' % url)
    log.debug('Login URL: %s.' % login_url)

    log.info("Opening URL: %s." % url)

    try:
        sess = requests.Session()
        sess.post(login_url, data={'username': username, 'password': password}, stream=True, verify=False)
        result = sess.get(url, params=params, stream=True, verify=False)

        for line in result.iter_lines():
            if line:
                log.info(line.strip())

    except IOError:
        e = sys.exc_info()[1]
        log.exception("Unable to open URL: %s." % str(e))
        sys.exit(1)


if __name__ == "__main__":
    log.error("This module is supposed to be used as import in other scripts and not run standalone.")
    sys.exit(1)