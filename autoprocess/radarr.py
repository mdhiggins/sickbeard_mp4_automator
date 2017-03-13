import sys
import os
import logging
import json


def processMovie(dirName, settings, nzbGet=False, logger=None):

    if nzbGet:
        errorprefix = "[ERROR] "
        infoprefix = "[INFO] "
    else:
        errorprefix = ""
        infoprefix = ""

    # Setup logging
    if logger:
        log = logger
    else:
        log = logging.getLogger(__name__)

    log.info("%sRadarr notifier started." % infoprefix)

    # Import Requests
    try:
        import requests
    except ImportError:
        log.exception("%sPython module REQUESTS is required. Install with 'pip install requests' then try again." % errorprefix)
        log.error("%sPython executable path is %s" % (errorprefix, sys.executable))
        return False

    host = settings.Radarr['host']
    port = settings.Radarr['port']
    apikey = settings.Radarr['apikey']

    if apikey == '':
        log.error("%sYour Radarr API Key can not be blank. Update autoProcess.ini." % errorprefix)
        return False

    try:
        ssl = int(settings.Radarr['ssl'])
    except:
        ssl = 0
    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    url = protocol + host + ":" + port + "/api/command"
    payload = {'name': 'DownloadedMoviesScan', 'path': dirName}
    headers = {'X-Api-Key': apikey}

    log.debug("Radarr host: %s." % host)
    log.debug("Radarr port: %s." % port)
    log.debug("Radarr apikey: %s." % apikey)
    log.debug("Radarr protocol: %s." % protocol)
    log.debug("URL '%s' with payload '%s.'" % (url, payload))

    log.info("%sRequesting Radarr to scan directory '%s'." % (infoprefix, dirName))

    try:
        r = requests.post(url, data=json.dumps(payload), headers=headers)
        rstate = r.json()
        log.info("%sRadarr response: %s." % (infoprefix, rstate['state']))
        return True
    except:
        log.exception("%sUpdate to Radarr failed, check if Radarr is running, autoProcess.ini settings and make sure your Radarr settings are correct (apikey?), or check install of python modules requests." % errorprefix)
        return False
