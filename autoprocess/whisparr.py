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

    log.info("%sWhisparr notifier started." % infoprefix)

    # Path Mapping
    targetdirs = dirName.split(os.sep)
    for k in sorted(pathMapping.keys(), reverse=True):
        mapdirs = k.split(os.sep)
        if mapdirs == targetdirs[:len(mapdirs)]:
            dirName = os.path.normpath(os.path.join(pathMapping[k], os.path.relpath(dirName, k)))
            log.debug("PathMapping match found, replacing %s with %s, final directory is %s." % (k, pathMapping[k], dirName))
            break

    # Import Requests
    try:
        import requests
    except ImportError:
        log.exception("%sPython module REQUESTS is required. Install with 'pip install requests' then try again." % errorprefix)
        log.error("%sPython executable path is %s" % (errorprefix, sys.executable))
        return False

    host = settings.Whisparr['host']
    port = settings.Whisparr['port']
    apikey = settings.Whisparr['apikey']

    if apikey == '':
        log.error("%sYour Whisparr API Key can not be blank. Update autoProcess.ini." % errorprefix)
        return False

    try:
        ssl = int(settings.Whisparr['ssl'])
    except:
        ssl = 0
    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    webroot = settings.Whisparr['webroot']
    url = protocol + host + ":" + str(port) + webroot + "/api/v3/command"
    payload = {'name': 'DownloadedEpisodesScan', 'path': dirName}
    if importMode:
        payload["importMode"] = importMode
    headers = {
        'X-Api-Key': apikey,
        'User-Agent': "SMA - autoprocess/whisparr"
    }

    log.debug("Whisparr host: %s." % host)
    log.debug("Whisparr port: %s." % port)
    log.debug("Whisparr webroot: %s." % webroot)
    log.debug("Whisparr apikey: %s." % apikey)
    log.debug("Whisparr protocol: %s." % protocol)
    log.debug("URL '%s' with payload '%s.'" % (url, payload))

    log.info("%sRequesting Whisparr to scan directory '%s'." % (infoprefix, dirName))

    try:
        r = requests.post(url, json=payload, headers=headers)
        rstate = r.json()
        log.debug(rstate)
        try:
            rstate = rstate[0]
        except:
            pass
        log.info("%sWhisparr response DownloadedMoviesScan command: ID %s %s." % (infoprefix, rstate['id'], rstate['status']))
        return True
    except:
        log.exception("%sUpdate to Whisparr failed, check if Whisparr is running, autoProcess.ini settings and make sure your Whisparr settings are correct (apikey?), or check install of python modules requests." % errorprefix)
        return False
