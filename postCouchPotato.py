#!/usr/bin/env python

import sys
import os
import logging
from log import getLogger
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4
from metadata import Metadata, MediaType
from autoprocess import plex
from post_processor import PostProcessor
from logging.config import fileConfig

log = getLogger("CouchPotatoPostProcess")

log.info('MP4 Automator - Post processing script initialized')

settings = ReadSettings()
converter = MkvtoMp4(settings)

imdbid = sys.argv[1]
inputfile = sys.argv[2]
original = sys.argv[3]

log.debug("IMDBID: %s." % imdbid)
log.debug("Input file path: %s." % inputfile)
log.debug("Original file name: %s." % original)

try:
    log.info('Processing file: %s.', inputfile)

    info = converter.isValidSource(inputfile)
    if info:
        output = converter.process(inputfile, original=original, info=info)

        if output:
            # Tag with metadata
            try:
                tag = Metadata(MediaType.Movie, imdbid=imdbid, original=original, language=settings.taglanguage)
                if settings.tagfile:
                    log.info('Tagging file with TMDB ID %s.', tag.tmdbid)
                    tag.setHD(output['x'], output['y'])
                    tag.writeTags(output['output'], settings.artwork, settings.thumbnail)
            except:
                log.exception("Unable to tag file.")

            # QTFS
            if settings.relocate_moov:
                converter.QTFS(output['output'])

            # Copy to additional locations
            output_files = converter.replicate(output['output'])

            # Run any post process scripts
            if settings.postprocess:
                post_processor = PostProcessor(output_files, log)
                post_processor.setMovie(tag.tmdbid)
                post_processor.run_scripts()

            plex.refreshPlex(settings, 'movie', log)
    else:
        log.info('File %s is invalid, ignoring.' % inputfile)
except:
    log.exception('File processing failed: %s.' % inputfile)
