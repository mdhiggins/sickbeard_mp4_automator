#!/usr/bin/env python
import os
import sys
import logging
from extensions import valid_tagging_extensions
from readSettings import ReadSettings
from autoprocess import plex
from tmdb_mp4 import tmdb_mp4
from mkvtomp4 import MkvtoMp4
from post_processor import PostProcessor
from logging.config import fileConfig
import time
import requests

logpath = '/var/log/sickbeard_mp4_automator'
if os.name == 'nt':
    logpath = os.path.dirname(sys.argv[0])
elif not os.isdir(logpath):
    try:
        os.makedir(logpath)
    except:
        logpath = os.path.dirname(sys.argv[0])
fileConfig(os.path.join(os.path.dirname(sys.argv[0]), 'logging.ini'), defaults={'logfilename': os.path.join(logpath, 'index.log')})
log = logging.getLogger("RadarrPostConversion")

log.info("Radarr extra script post processing started.")

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")

log.info(os.environ)

inputfile = os.environ.get('radarr_moviefile_path')
original = os.environ.get('radarr_moviefile_scenename')
imdbid = os.environ.get('radarr_movie_imdbid')

converter = MkvtoMp4(settings)

log.debug("Input file: %s." % inputfile)
log.debug("Original name: %s." % original)
log.debug("IMDB ID: %s." % imdbid)

if MkvtoMp4(settings).validSource(inputfile):
    log.info("Processing %s." % inputfile)

    output = converter.process(inputfile, original=original)

    if output:
        # Tag with metadata
        if settings.tagfile and output['output_extension'] in valid_tagging_extensions:
            log.info('Tagging file with IMDB ID %s', imdbid)
            try:
                tagmp4 = tmdb_mp4(imdbid, original=original, language=settings.taglanguage)
                tagmp4.setHD(output['x'], output['y'])
                tagmp4.writeTags(output['output'], settings.artwork, settings.thumbnail)
            except:
                log.error("Unable to tag file")

        # QTFS
        if settings.relocate_moov and output['output_extension'] in valid_tagging_extensions:
            converter.QTFS(output['output'])

        # Copy to additional locations
        output_files = converter.replicate(output['output'])

        # Update Radarr to continue monitored status
        try:
            host = settings.Radarr['host']
            port = settings.Radarr['port']
            webroot = settings.Radarr['web_root']
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
                url = protocol + host + ":" + port + webroot + "/api/command"
                r = requests.post(url, json=payload, headers=headers)
                rstate = r.json()
                log.info("Radarr response: ID %d %s." % (rstate['id'], rstate['state']))
                log.debug(str(rstate))

                # Then wait for it to finish
                url = protocol + host + ":" + port + webroot + "/api/command/" + str(rstate['id'])
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
                url = protocol + host + ":" + port + webroot + "/api/movie/" + movieID
                log.info("Requesting updated information from Radarr for movie ID %s." % movieID)
                r = requests.get(url, headers=headers)
                payload = r.json()
                payload['monitored'] = True

                # Then set that movie to monitored
                log.debug("Sending PUT request with following payload:")
                log.info(str(payload)) # debug

                url = protocol + host + ":" + port + webroot + "/api/movie/" + str(movieID)
                r = requests.put(url, json=payload, headers=headers)
                success = r.json()

                log.debug("PUT request returned:")
                log.debug(str(success))
                log.info("Radarr monitoring information updated for movie %s." % success['title'])
            else:
                log.error("Your Radarr API Key can not be blank. Update autoProcess.ini.")
        except:
            log.exception("Radarr monitor status update failed.")

        # run any post process scripts
        if settings.postprocess:
            post_processor = PostProcessor(output_files, log)
            post_processor.setMovie(imdbid)
            post_processor.run_scripts()

        plex.refreshPlex(settings, 'movie', log)
