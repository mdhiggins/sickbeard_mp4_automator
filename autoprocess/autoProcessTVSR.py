#!/usr/bin/env python3

#
# This file is adapted from the autoProcessTV file included with SickRage.
#

from __future__ import with_statement

import os
import sys
import logging

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), 'lib')))


def processEpisode(dir_to_process, settings, org_NZB_name=None, status=None, logger=None, pathMapping={}):
    log = logger or logging.getLogger(__name__)

    # Path Mapping
    targetdirs = dirName.split(os.sep)
    for k in sorted(pathMapping.keys(), reverse=True):
        mapdirs = k.split(os.sep)
        if mapdirs == targetdirs[:len(mapdirs)]:
            dirName = os.path.join(pathMapping[k], os.path.relpath(dirName, k))
            log.debug("PathMapping match found, replacing %s with %s, final directory is %s." % (k, pathMapping[k], dirName))
            break

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
    apikey = settings.Sickrage['apikey']

    if apikey == '':
        log.error("Your Sickrage API Key can not be blank. Update autoProcess.ini.")
        sys.exit(1)

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

    params = {
        'cmd': 'postprocess',
        'return_data': 0,
        'path': dir_to_process
    }

    if org_NZB_name is not None:
        params['nzbName'] = org_NZB_name

    if status is not None:
        params['failed'] = status

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    url = "{}{}:{}{}api/{}/".format(protocol, host, port, webroot, apikey)

    log.debug('Host: %s.' % host)
    log.debug('Port: %s.' % port)
    log.debug('Sickrage apikey: %s.' % apikey)
    log.debug('Protocol: %s.' % protocol)
    log.debug('Web Root: %s.' % webroot)
    log.debug('URL: %s.' % url)
    log.debug('Params: %s.' % params)

    log.info("Opening URL: %s." % url)

    try:
        r = requests.get(url, params=params, verify=False, allow_redirects=False, stream=True)

        for line in r.iter_lines():
            if line:
                log.debug(line.strip())
                lastline = line.strip()

        if lastline:
            log.info(lastline)

    except IOError:
        e = sys.exc_info()[1]
        log.exception("Unable to open URL: %s." % str(e))
        sys.exit(1)
