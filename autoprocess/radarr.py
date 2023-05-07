import sys
import os
import logging


def processMovie(dirName, settings, nzbGet=False, importMode=None, logger=None, pathMapping={}):

    if nzbGet:
        errorprefix = "[ERROR] "
        infoprefix = "[INFO] "
    else:
        errorprefix = ""
        infoprefix = ""

    log = logger or logging.getLogger(__name__)

    log.info("%sRadarr notifier started." % infoprefix)

    # Path Mapping
    targetdirs = dirName.split(os.sep)
    for k in sorted(pathMapping.keys(), reverse=True):
        mapdirs = k.split(os.sep)
        if mapdirs == targetdirs[:len(mapdirs)]:
            dirName = os.path.join(pathMapping[k], os.path.relpath(dirName, k))
            log.debug("PathMapping match found, replacing %s with %s, final directory is %s." % (k, pathMapping[k], dirName))
            break

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

    webroot = settings.Radarr['webroot']
    url = protocol + host + ":" + str(port) + webroot + "/api/v3/command"
    payload = {'name': 'DownloadedMoviesScan', 'path': dirName}
    if importMode:
        payload["importMode"] = importMode
    headers = {
        'X-Api-Key': apikey,
        'User-Agent': "SMA - autoprocess/radarr"
    }

    log.debug("Radarr host: %s." % host)
    log.debug("Radarr port: %s." % port)
    log.debug("Radarr webroot: %s." % webroot)
    log.debug("Radarr apikey: %s." % apikey)
    log.debug("Radarr protocol: %s." % protocol)
    log.debug("URL '%s' with payload '%s.'" % (url, payload))

    log.info("%sRequesting Radarr to scan directory '%s'." % (infoprefix, dirName))

    try:
        r = requests.post(url, json=payload, headers=headers)
        rstate = r.json()
        log.debug(rstate)
        try:
            rstate = rstate[0]
        except:
            pass
        log.info("%sRadarr response DownloadedMoviesScan command: ID %s %s." % (infoprefix, rstate['id'], rstate['status']))
        return True
    except:
        log.exception("%sUpdate to Radarr failed, check if Radarr is running, autoProcess.ini settings and make sure your Radarr settings are correct (apikey?), or check install of python modules requests." % errorprefix)
        return False
