#!/usr/bin/env python3
import os
import sys
import json
import urllib
import struct
from resources.log import getLogger
from resources.readsettings import ReadSettings
from resources.metadata import MediaType
from resources.mediaprocessor import MediaProcessor

log = getLogger("SickbeardPostProcess")

log.info("Sickbeard extra script post processing started.")

try:
    settings = ReadSettings()

    if len(sys.argv) > 4:
        inputfile = sys.argv[1]
        original = sys.argv[2]
        tvdb_id = int(sys.argv[3])
        season = int(sys.argv[4])
        episode = int(sys.argv[5])

        log.debug("Input file: %s." % inputfile)
        log.debug("Original name: %s." % original)
        log.debug("TVDB ID: %s." % tvdb_id)
        log.debug("Season: %s episode: %s." % (season, episode))

        mp = MediaProcessor(settings)

        success = mp.fullprocess(inputfile, MediaType.TV, tvdbid=tvdb_id, season=season, episode=episode, original=original)
        if success:
            try:
                protocol = "https://" if settings.Sickbeard['ssl'] else "http://"
                host = settings.Sickbeard['host']  # Server Address
                port = settings.Sickbeard['port']  # Server Port
                apikey = settings.Sickbeard['apikey']  # Sickbeard API key
                webroot = settings.Sickbeard['webroot']  # Sickbeard webroot

                sickbeard_url = protocol + host + ":" + str(port) + webroot + "/api/" + apikey + "/?cmd=show.refresh&tvdbid=" + str(tvdb_id)

                refresh = json.load(urllib.urlopen(sickbeard_url))
                for item in refresh:
                    log.debug(refresh[item])
            except (IOError, ValueError):
                log.exception("Couldn't refresh Sickbeard, check your autoProcess.ini settings.")
    else:
        log.error("Not enough command line arguments present %s." % len(sys.argv))
        sys.exit(1)
except:
    log.exception("Unexpected exception.")
    sys.exit(1)
