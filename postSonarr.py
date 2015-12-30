#!/usr/bin/env python
import os
import sys
import logging
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
            tagmp4 = Tvdb_mp4(tvdb_id, season, episode, original, language=settings.taglanguage)
            tagmp4.setHD(output['x'], output['y'])
            tagmp4.writeTags(output['output'], settings.artwork, settings.thumbnail)

        # QTFS
        if settings.relocate_moov:
            converter.QTFS(output['output'])

        # Copy to additional locations
        output_files = converter.replicate(output['output'])

        # run any post process scripts
        if settings.postprocess:
            post_processor = PostProcessor(output_files, log)
            post_processor.setTV(tvdb_id, season, episode)
            post_processor.run_scripts()

        plex.refreshPlex(settings, 'show', log)
