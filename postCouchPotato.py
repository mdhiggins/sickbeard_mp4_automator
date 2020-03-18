#!/usr/bin/env python3

import sys
import os
import logging
from resources.log import getLogger
from resources.readsettings import ReadSettings
from resources.mediaprocessor import MediaProcessor
from resources.metadata import MediaType

log = getLogger("CouchPotatoPostProcess")

log.info('MP4 Automator - Post processing script initialized')

try:
    settings = ReadSettings()
    mp = MediaProcessor(settings)

    imdbid = sys.argv[1]
    inputfile = sys.argv[2]
    original = sys.argv[3]

    log.debug("IMDBID: %s." % imdbid)
    log.debug("Input file path: %s." % inputfile)
    log.debug("Original file name: %s." % original)

    success = mp.fullprocess(inputfile, MediaType.Movie, imdbid=imdbid, original=original)
    log.info("Processor returned %s." % success)
except:
    log.exception("Unexpected exception.")
    sys.exit(1)
