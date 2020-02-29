#!/usr/bin/env python
import os
import sys
import json
import urllib
import struct
import logging
from log import getLogger
from readSettings import ReadSettings
from autoprocess import plex
from metadata import Metadata, MediaType
from mkvtomp4 import MkvtoMp4
from post_processor import PostProcessor
from logging.config import fileConfig

log = getLogger("SickbeardPostProcess")

log.info("Sickbeard extra script post processing started.")

settings = ReadSettings()

if len(sys.argv) > 4:
    inputfile = sys.argv[1]
    original = sys.argv[2]
    tvdb_id = int(sys.argv[3])
    season = int(sys.argv[4])
    episode = int(sys.argv[5])

    converter = MkvtoMp4(settings)

    log.debug("Input file: %s." % inputfile)
    log.debug("Original name: %s." % original)
    log.debug("TVDB ID: %s." % tvdb_id)
    log.debug("Season: %s episode: %s." % (season, episode))

    info = converter.isValidSource(inputfile)
    if info:
        log.info("Processing %s." % inputfile)

        output = converter.process(inputfile, original=original, info=info)

        if output:
            # Tag with metadata
            try:
                tag = Metadata(MediaType.TV, tvdbid=tvdb_id, season=season, episode=episode, original=original, language=settings.taglanguage)
                if settings.tagfile:
                    log.info("Tagging %s with ID %s season %s episode %s." % (inputfile, tvdb_id, season, episode))
                    tag.setHD(output['x'], output['y'])
                    tag.writeTags(output['output'], settings.artwork, settings.thumbnail)
            except:
                log.exception("Unable to tag file")

            # QTFS
            if settings.relocate_moov:
                converter.QTFS(output['output'])

            # Copy to additional locations
            output_files = converter.replicate(output['output'])

            # Run any post process scripts
            if settings.postprocess:
                post_processor = PostProcessor(output_files, log)
                post_processor.setTV(tag.tmdbid, tag.season, tag.episode)
                post_processor.run_scripts()

            try:
                refresh = json.load(urllib.urlopen(settings.getRefreshURL(tvdb_id)))
                for item in refresh:
                    log.debug(refresh[item])
            except (IOError, ValueError):
                log.exception("Couldn't refresh Sickbeard, check your autoProcess.ini settings.")

            plex.refreshPlex(settings, 'show', log)

else:
    log.error("Not enough command line arguments present %s." % len(sys.argv))
    sys.exit()
