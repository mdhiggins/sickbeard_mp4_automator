#!/usr/bin/env python
import os
import sys
import logging
from readSettings import ReadSettings
from autoprocess import plex
from tmdb_mp4 import tmdb_mp4
from mkvtomp4 import MkvtoMp4
from post_processor import PostProcessor
from logging.config import fileConfig

fileConfig(os.path.join(os.path.dirname(sys.argv[0]), 'logging.ini'), defaults={'logfilename': os.path.join(os.path.dirname(sys.argv[0]), 'info.log')})
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
        if settings.tagfile:
            log.info('Tagging file with IMDB ID %s', imdbid)
            tagmp4 = tmdb_mp4(imdbid, original=original, language=settings.taglanguage)
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
            post_processor.setMovie(imdbid)
            post_processor.run_scripts()

        plex.refreshPlex(settings, 'movie', log)
