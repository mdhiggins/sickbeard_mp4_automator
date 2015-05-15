#!/usr/bin/env python

import os
import sys
from autoprocess import autoProcessTV, autoProcessMovie, autoProcessTVSR, sonarr
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4
import logging
from logging.config import fileConfig

fileConfig(os.path.join(os.path.dirname(sys.argv[0]), 'logging.ini'), defaults={'logfilename': os.path.join(os.path.dirname(sys.argv[0]), 'info.log').replace("\\", "/")})
log = logging.getLogger("SABPostProcess")

log.info("SAB post processing started.")

if len(sys.argv) < 8:
    log.error("Not enough command line parameters specified. Is this being called from SAB?")
    sys.exit()

# SABnzbd argv:
# 1 The final directory of the job (full path)
# 2 The original name of the NZB file
# 3 Clean version of the job name (no path info and ".nzb" removed)
# 4 Indexer's report number (if supported)
# 5 User-defined category
# 6 Group that the NZB was posted in e.g. alt.binaries.x
# 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
categories = [settings.SAB['sb'], settings.SAB['cp'], settings.SAB['sonarr'], settings.SAB['sr'], settings.SAB['bypass']]
category = str(sys.argv[5]).lower()
path = str(sys.argv[1])
nzb = str(sys.argv[2])

log.debug("Path: %s." % path)
log.debug("Category: %s." % category)
log.debug("Categories: %s." % categories)
log.debug("NZB: %s." % nzb)

if category.lower() not in categories:
    log.error("No valid category detected.")
    sys.exit()

if len(categories) != len(set(categories)):
    log.error("Duplicate category detected. Category names must be unique.")
    sys.exit()

if settings.SAB['convert']:
    log.info("Performing conversion")
    converter = MkvtoMp4(settings)
    converter.output_dir = None
    for r, d, f in os.walk(path):
        for files in f:
            inputfile = os.path.join(r, files)
            if MkvtoMp4(settings).validSource(inputfile):
                log.info("Processing file %s." % inputfile)
                try:
                    output = converter.process(inputfile)
                    if (category == categories[2] and settings.relocate_moov):
                        log.debug("Performing QTFS move because video was converted and Sonarr has no post processing.")
                        converter.QTFS(output['output'])
                except:
                    log.exception("Error converting file %s." % inputfile)
            else:
                log.debug("Ignoring file %s." % inputfile)
else:
    log.info("Passing without conversion.")

# Send to Sickbeard
if (category == categories[0]):
    log.info("Passing %s directory to Sickbeard." % path)
    autoProcessTV.processEpisode(path, settings, nzb)
# Send to CouchPotato
elif (category == categories[1]):
    log.info("Passing %s directory to Couch Potato." % path)
    autoProcessMovie.process(path, settings, nzb, sys.argv[7])
# Send to Sonarr
elif (category == categories[2]):
    log.info("Passing %s directory to Sonarr." % path)
    sonarr.processEpisode(path, settings)
elif (category == categories[3]):
    log.info("Passing %s directory to Sickrage." % path)
    autoProcessTVSR.processEpisode(path, settings, nzb)
# Bypass
elif (category == categories[4]):
    log.info("Bypassing any further processing as per category.")
