#!/usr/bin/env python3

#
# This file is adapted from the autoProcessTV file included with SickRage.
#

from __future__ import with_statement

import os.path
import sys
import logging

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), 'lib')))


def processEpisode(dir_to_process, settings, org_NZB_name=None, status=None, logger=None):
    log = logger or logging.getLogger(__name__)

    try:
        import requests
    except ImportError:
        log.exception("You need to install python requests library.")
        sys.exit(1)

    # Try importing Python 2 modules using new names
    try:
        from urllib import urlencode
    # On error import Python 3 modules
    except ImportError:
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
        webroot = settings.Sickrage['webroot']
        if not webroot.startswith("/"):
            webroot = "/" + webroot
        if not webroot.endswith("/"):
            webroot = webroot + "/"
    except:
        webroot = ""

    params = {}

    params['quiet'] = 1

    params['dir'] = dir_to_process
    if org_NZB_name is not None:
        params['nzbName'] = org_NZB_name

    if status is not None:
        params['failed'] = status

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    url = protocol + host + ":" + str(port) + webroot + "home/postprocess/processEpisode"
    login_url = protocol + host + ":" + str(port) + webroot + "login"

    log.debug('Host: %s.' % host)
    log.debug('Port: %s.' % port)
    log.debug('Username: %s.' % username)
    log.debug('Password: %s.' % password)
    log.debug('Protocol: %s.' % protocol)
    log.debug('Web Root: %s.' % webroot)
    log.debug('URL: %s.' % url)
    log.debug('Login URL: %s.' % login_url)

    log.info("Opening URL: %s." % url)

    try:
        sess = requests.Session()
        sess.post(login_url, data={'username': username, 'password': password}, stream=True, verify=False)
        result = sess.get(url, params=params, stream=True, verify=False)
        lastline = None

        for line in result.iter_lines():
            if line:
                log.debug(line.strip())
                lastline = line.strip()

        if lastline:
            log.info(lastline)

    except IOError:
        e = sys.exc_info()[1]
        log.exception("Unable to open URL: %s." % str(e))
        sys.exit(1)
