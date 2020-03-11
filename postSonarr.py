#!/usr/bin/env python
import os
import sys
import requests
import time
from resources.log import getLogger
from resources.readsettings import ReadSettings
from resources.metadata import MediaType
from resources.mediaprocessor import MediaProcessor

log = getLogger("SonarrPostProcess")

log.info("Sonarr extra script post processing started.")

if os.environ.get('sonarr_eventtype') == "Test":
    sys.exit(0)

settings = ReadSettings()

inputfile = os.environ.get('sonarr_episodefile_path')
original = os.environ.get('sonarr_episodefile_scenename')
tvdb_id = int(os.environ.get('sonarr_series_tvdbid'))
season = int(os.environ.get('sonarr_episodefile_seasonnumber'))

try:
    episode = int(os.environ.get('sonarr_episodefile_episodenumbers'))
except:
    episode = int(os.environ.get('sonarr_episodefile_episodenumbers').split(",")[0])

mp = MediaProcessor(settings)

log.debug("Input file: %s." % inputfile)
log.debug("Original name: %s." % original)
log.debug("TVDB ID: %s." % tvdb_id)
log.debug("Season: %s episode: %s." % (season, episode))

try:
    success = mp.fullprocess(inputfile, MediaType.TV, tvdbid=tvdb_id, season=season, episode=episode, original=original)

    if success:
        # Update Sonarr to continue monitored status
        try:
            host = settings.Sonarr['host']
            port = settings.Sonarr['port']
            webroot = settings.Sonarr['webroot']
            apikey = settings.Sonarr['apikey']
            if apikey != '':
                try:
                    ssl = int(settings.Sonarr['ssl'])
                except:
                    ssl = 0
                if ssl:
                    protocol = "https://"
                else:
                    protocol = "http://"

                seriesID = os.environ.get('sonarr_series_id')
                log.debug("Sonarr host: %s." % host)
                log.debug("Sonarr port: %s." % port)
                log.debug("Sonarr webroot: %s." % webroot)
                log.debug("Sonarr apikey: %s." % apikey)
                log.debug("Sonarr protocol: %s." % protocol)
                log.debug("Sonarr sonarr_series_id: %s." % seriesID)
                headers = {'X-Api-Key': apikey}

                # First trigger rescan
                payload = {'name': 'RescanSeries', 'seriesId': seriesID}
                url = protocol + host + ":" + str(port) + webroot + "/api/command"
                r = requests.post(url, json=payload, headers=headers)
                rstate = r.json()
                try:
                    rstate = rstate[0]
                except:
                    pass
                log.info("Sonarr response: ID %d %s." % (rstate['id'], rstate['state']))
                log.debug(str(rstate))

                # Then wait for it to finish
                url = protocol + host + ":" + str(port) + webroot + "/api/command/" + str(rstate['id'])
                log.info("Requesting episode information from Sonarr for series ID %s." % seriesID)
                r = requests.get(url, headers=headers)
                command = r.json()
                attempts = 0
                while command['state'].lower() not in ['complete', 'completed'] and attempts < 6:
                    log.info(str(command['state']))
                    time.sleep(10)
                    r = requests.get(url, headers=headers)
                    command = r.json()
                    attempts += 1
                log.info("Command completed.")
                log.info(str(command))

                # Then get episode information
                url = protocol + host + ":" + str(port) + webroot + "/api/episode?seriesId=" + seriesID
                log.info("Requesting updated episode information from Sonarr for series ID %s." % seriesID)
                r = requests.get(url, headers=headers)
                payload = r.json()
                sonarrepinfo = None
                for ep in payload:
                    if int(ep['episodeNumber']) == episode and int(ep['seasonNumber']) == season:
                        sonarrepinfo = ep
                        break
                sonarrepinfo['monitored'] = True

                # Then set that episode to monitored
                log.debug("Sending PUT request with following payload:")
                log.debug(str(sonarrepinfo))

                url = protocol + host + ":" + str(port) + webroot + "/api/episode/" + str(sonarrepinfo['id'])
                r = requests.put(url, json=sonarrepinfo, headers=headers)
                success = r.json()

                log.debug("PUT request returned:")
                log.debug(str(success))
                log.info("Sonarr monitoring information updated for episode %s." % success['title'])
            else:
                log.error("Your Sonarr API Key can not be blank. Update autoProcess.ini.")
        except:
            log.exception("Sonarr monitor status update failed.")
    else:
        log.info("Processing returned False.")
        sys.exit(1)
except:
    log.exception("Error processing file")
    sys.exit(1)
sys.exit(0)
