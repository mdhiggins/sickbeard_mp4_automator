import sys
import os
import logging
from logging.config import fileConfig

def processEpisode(dirName, settings, nzbGet=False):

    if nzbGet:
        errorprefix = "[ERROR] "
        infoprefix = "[INFO] "
    else:
        errorprefix = ""
        infoprefix = ""

    #fileConfig(os.path.join(os.path.dirname(sys.argv[0]), 'logging.ini'), defaults={'logfilename': os.path.join(os.path.dirname(sys.argv[0]), 'info.log')})
    log = logging.getLogger(__name__)

    log.info("%sSonarr notifier started." % infoprefix)

    # Import Requests
    try:
        import requests
    except ImportError:
        log.exception("%sPython module REQUESTS is required. Install with 'pip install requests' then try again." % errorprefix)
        return False

    host=settings.Sonarr['host']
    port=settings.Sonarr['port']
    apikey = settings.Sonarr['apikey']

    if apikey == '':
        log.error("%sYour Sonarr API Key can not be blank. Update autoProcess.ini." % errorprefix)
        return False

    try:
        ssl=int(settings.Sonarr['ssl'])
    except:
        ssl=0
    if ssl:
        protocol="https://"
    else:
        protocol="http://"

    url = protocol+host+":"+port+"/api/command"
    payload = {'name': 'downloadedepisodesscan','path': dirName}
    headers = {'X-Api-Key': apikey}

    log.debug("Sonarr host: %s." % host)
    log.debug("Sonarr port: %s." % port)
    log.debug("Sonarr apikey: %s." % apikey)
    log.debug("Sonarr protocol: %s." % protocol)
    log.debug("URL '%s' with payload '%s.'" % (url, payload))

    log.info("%sRequesting Sonarr to scan directory '%s'." % (infoprefix, dirName))

    try:
        r = requests.post(url, data=json.dumps(payload), headers=headers)
        rstate = r.json()
        log.info("%sSonarr response: %s." % (infoprefix, rstate['state']))
        return True
    except:
        log.exception("%sUpdate to Sonarr failed, check if Sonarr is running, autoProcess.ini for errors, or check install of python modules requests." % errorprefix)
        return False