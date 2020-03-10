#!/usr/bin/env python
import os
import sys
import requests
import time
from resources.log import getLogger
from resources.readsettings import ReadSettings
from resources.metadata import MediaType
from resources.mediaprocessor import MediaProcessor

log = getLogger("RadarrPostProcess")

log.info("Radarr extra script post processing started.")

if os.environ.get('radarr_eventtype') == "Test":
    sys.exit(0)

settings = ReadSettings()

log.info(os.environ)

inputfile = os.environ.get('radarr_moviefile_path')
original = os.environ.get('radarr_moviefile_scenename')
imdbid = os.environ.get('radarr_movie_imdbid')

mp = MediaProcessor(settings, logger=log)

log.debug("Input file: %s." % inputfile)
log.debug("Original name: %s." % original)
log.debug("IMDB ID: %s." % imdbid)

try:
    success = mp.fullprocess(inputfile, MediaType.Movie, original=original, imdbid=imdbid)

    if success:
        # Update Radarr to continue monitored status
        try:
            host = settings.Radarr['host']
            port = settings.Radarr['port']
            webroot = settings.Radarr['webroot']
            apikey = settings.Radarr['apikey']
            if apikey != '':
                try:
                    ssl = int(settings.Radarr['ssl'])
                except:
                    ssl = 0
                if ssl:
                    protocol = "https://"
                else:
                    protocol = "http://"

                movieID = os.environ.get('radarr_movie_id')
                log.debug("Radarr host: %s." % host)
                log.debug("Radarr port: %s." % port)
                log.debug("Radarr webroot: %s." % webroot)
                log.debug("Radarr apikey: %s." % apikey)
                log.debug("Radarr protocol: %s." % protocol)
                log.debug("Radarr radarr_movie_id: %s." % movieID)
                headers = {'X-Api-Key': apikey}

                # First trigger rescan
                payload = {'name': 'RescanMovie', 'movieId': movieID}
                url = protocol + host + ":" + str(port) + webroot + "/api/command"
                r = requests.post(url, json=payload, headers=headers)
                rstate = r.json()
                try:
                    rstate = rstate[0]
                except:
                    pass
                log.info("Radarr response: ID %d %s." % (rstate['id'], rstate['state']))
                log.debug(str(rstate))

                # Then wait for it to finish
                url = protocol + host + ":" + str(port) + webroot + "/api/command/" + str(rstate['id'])
                log.info("Waiting rescan to complete")
                r = requests.get(url, headers=headers)
                command = r.json()
                attempts = 0
                while command['state'].lower() not in ['complete', 'completed'] and attempts < 6:
                    log.info(str(command['state']))
                    time.sleep(10)
                    r = requests.get(url, headers=headers)
                    command = r.json()
                    attempts += 1
                log.info("Command completed")
                log.debug(str(command))

                # Then get movie information
                url = protocol + host + ":" + str(port) + webroot + "/api/movie/" + movieID
                log.info("Requesting updated information from Radarr for movie ID %s." % movieID)
                r = requests.get(url, headers=headers)
                payload = r.json()
                payload['monitored'] = True

                # Then set that movie to monitored
                log.debug("Sending PUT request with following payload:")
                log.info(str(payload))  # debug

                url = protocol + host + ":" + str(port) + webroot + "/api/movie/" + str(movieID)
                r = requests.put(url, json=payload, headers=headers)
                success = r.json()

                log.debug("PUT request returned:")
                log.debug(str(success))
                log.info("Radarr monitoring information updated for movie %s." % success['title'])
            else:
                log.error("Your Radarr API Key can not be blank. Update autoProcess.ini.")
        except:
            log.exception("Radarr monitor status update failed.")
    else:
        log.info("Processing returned False.")
except:
    log.exception("Error processing file")
    sys.exit(1)
sys.exit(0)
