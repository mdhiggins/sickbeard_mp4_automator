#!/usr/bin/env python

import sys
import os
import logging
from extensions import valid_tagging_extensions
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4
from tmdb_mp4 import tmdb_mp4
from autoprocess import plex
from post_processor import PostProcessor
from logging.config import fileConfig

fileConfig(os.path.join(os.path.dirname(sys.argv[0]), 'logging.ini'), defaults={'logfilename': os.path.join(os.path.dirname(sys.argv[0]), 'info.log')})
log = logging.getLogger("CouchPotatoPostConversion")

log.info('MP4 Automator - Post processing script initialized')

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
converter = MkvtoMp4(settings)

imdbid = sys.argv[1]
inputfile = sys.argv[2]
original = sys.argv[3]

log.debug("IMDBID: %s" % imdbid)
log.debug("Input file path: %s" % inputfile)
log.debug("Original file name: %s" % original)

try:
    log.info('Processing file: %s', inputfile)
    if MkvtoMp4(settings).validSource(inputfile):
        log.info('File is valid')
        output = converter.process(inputfile, original=original)

        if output:
            # Tag with metadata
            if settings.tagfile and output['output_extension'] in valid_tagging_extensions:
                log.info('Tagging file with IMDB ID %s', imdbid)
                try:
                    tagmp4 = tmdb_mp4(imdbid, original=original, language=settings.taglanguage)
                    tagmp4.setHD(output['x'], output['y'])
                    tagmp4.writeTags(output['output'], settings.artwork)
                except:
                    log.error("Unable to tag file")

            # QTFS
            if settings.relocate_moov and output['output_extension'] in valid_tagging_extensions:
                converter.QTFS(output['output'])

            # Copy to additional locations
            output_files = converter.replicate(output['output'])

            # Run any post process scripts
            if settings.postprocess:
                post_processor = PostProcessor(output_files, log)
                post_processor.setMovie(imdbid)
                post_processor.run_scripts()

            plex.refreshPlex(settings, 'movie', log)
    else:
        log.info('File %s is invalid, ignoring' % inputfile)
except:
    log.exception('File processing failed: %s' % inputfile)
