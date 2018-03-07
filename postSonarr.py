#!/usr/bin/env python
import os
import sys
import logging
import requests
import time
from readSettings import ReadSettings
from autoprocess import plex
from tvdb_mp4 import Tvdb_mp4
from mkvtomp4 import MkvtoMp4
from post_processor import PostProcessor
from logging.config import fileConfig

fileConfig(os.path.join(os.path.dirname(sys.argv[0]), 'logging.ini'), defaults={'logfilename': os.path.join(os.path.dirname(sys.argv[0]), 'info.log')})
log = logging.getLogger("SonarrPostConversion")

log.info("Sonarr extra script post processing started.")

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")

inputfile = os.environ.get('sonarr_episodefile_path')
original = os.environ.get('sonarr_episodefile_scenename')
tvdb_id = int(os.environ.get('sonarr_series_tvdbid'))
season = int(os.environ.get('sonarr_episodefile_seasonnumber'))

try:
    episode = int(os.environ.get('sonarr_episodefile_episodenumbers'))
except:
    episode = int(os.environ.get('sonarr_episodefile_episodenumbers').split(",")[0])

converter = MkvtoMp4(settings)

log.debug("Input file: %s." % inputfile)
log.debug("Original name: %s." % original)
log.debug("TVDB ID: %s." % tvdb_id)
log.debug("Season: %s episode: %s." % (season, episode))

if MkvtoMp4(settings).validSource(inputfile):
    log.info("Processing %s." % inputfile)

    output = converter.process(inputfile, original=original)

    if output:
        # Tag with metadata
        if settings.tagfile:
            log.info("Tagging %s with ID %s season %s episode %s." % (inputfile, tvdb_id, season, episode))
            try:
                tagmp4 = Tvdb_mp4(tvdb_id, season, episode, original, language=settings.taglanguage)
                tagmp4.setHD(output['x'], output['y'])
                tagmp4.writeTags(output['output'], settings.artwork, settings.thumbnail)
            except:
                log.error("Unable to tag file")

        # QTFS
        if settings.relocate_moov:
            converter.QTFS(output['output'])

        # Copy to additional locations
        output_files = converter.replicate(output['output'])

        # Update Sonarr to continue monitored status
        try:
            host = settings.Sonarr['host']
            port = settings.Sonarr['port']
            webroot = settings.Sonarr['web_root']
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
                url = protocol + host + ":" + port + webroot + "/api/command"
                r = requests.post(url, json=payload, headers=headers)
                rstate = r.json()
                log.info("Sonarr response: ID %d %s." % (rstate['id'], rstate['state']))
                log.info(str(rstate)) # debug

                # Then wait for it to finish
                url = protocol + host + ":" + port + webroot + "/api/command/" + str(rstate['id'])
                log.info("Requesting episode information from Sonarr for series ID %s." % seriesID)
                r = requests.get(url, headers=headers)
                command = r.json()
                attempts = 0
                while command['state'].lower() not in ['complete', 'completed']  and attempts < 6:
                    log.info(str(command['state']))
                    time.sleep(10)
                    r = requests.get(url, headers=headers)
                    command = r.json()
                    attempts += 1
                log.info("Command completed")
                log.info(str(command))

                # Then get episode information
                url = protocol + host + ":" + port + webroot + "/api/episode?seriesId=" + seriesID
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
                log.info("Sending PUT request with following payload:") # debug
                log.info(str(sonarrepinfo)) # debug

                url = protocol + host + ":" + port + webroot + "/api/episode/" + str(sonarrepinfo['id'])
                r = requests.put(url, json=sonarrepinfo, headers=headers)
                success = r.json()

                log.info("PUT request returned:") # debug
                log.info(str(success)) # debug
                log.info("Sonarr monitoring information updated for episode %s." % success['title'])
            else:
                log.error("Your Sonarr API Key can not be blank. Update autoProcess.ini.")
        except:
            log.exception("Sonarr monitor status update failed.")

        # Run any post process scripts
        if settings.postprocess:
            post_processor = PostProcessor(output_files, log)
            post_processor.setTV(tvdb_id, season, episode)
            post_processor.run_scripts()

        plex.refreshPlex(settings, 'show', log)
