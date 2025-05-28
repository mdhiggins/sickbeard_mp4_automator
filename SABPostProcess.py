#!/usr/bin/env python3

import os
import sys
from autoprocess import autoProcessTV, autoProcessTVSR, sonarr, radarr
from resources.log import getLogger
from resources.readsettings import ReadSettings
from resources.mediaprocessor import MediaProcessor

log = getLogger("SABPostProcess")

log.info("SAB post processing started.")

if len(sys.argv) < 8:
    log.error("Not enough command line parameters specified. Is this being called from SAB?")
    sys.exit(1)

# SABnzbd argv:
# 1 The final directory of the job (full path)
# 2 The original name of the NZB file
# 3 Clean version of the job name (no path info and ".nzb" removed)
# 4 Indexer's report number (if supported)
# 5 User-defined category
# 6 Group that the NZB was posted in e.g. alt.binaries.x
# 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2


def progressOutput(timecode, debug):
    print("%d%%" % timecode)


try:
    settings = ReadSettings()
    categories = [settings.SAB['sb'], settings.SAB['sonarr'], settings.SAB['radarr'], settings.SAB['sr']] + settings.SAB['bypass']
    category = str(sys.argv[5]).lower().strip()
    path = str(sys.argv[1])
    nzb = str(sys.argv[2])
    path_mapping = settings.SAB['path-mapping']

    log.debug("Path: %s." % path)
    log.debug("Category: %s." % category)
    log.debug("Categories: %s." % categories)
    log.debug("NZB: %s." % nzb)

    if len([x for x in categories if x.startswith(category)]) < 1:
        log.error("No valid category detected.")
        sys.exit(1)

    if len(categories) != len(set(categories)):
        log.error("Duplicate category detected. Category names must be unique.")
        sys.exit(1)

    if settings.SAB['convert']:
        log.info("Performing conversion")
        # Check for custom SAB output directory
        if settings.SAB['output-dir']:
            settings.output_dir = settings.SAB['output-dir']
            log.debug("Overriding output_dir to %s." % settings.SAB['output-dir'])

        mp = MediaProcessor(settings)
        ignore = []
        for r, d, f in os.walk(path):
            for files in f:
                inputfile = os.path.join(r, files)
                info = mp.isValidSource(inputfile)
                if info and inputfile not in ignore:
                    log.info("Processing file %s." % inputfile)
                    try:
                        output = mp.process(inputfile, reportProgress=True, info=info, progressOutput=progressOutput)
                        if output and output.get('output'):
                            log.info("Successfully processed %s." % inputfile)
                            ignore.append(output.get('output'))
                        else:
                            log.error("Converting file failed %s." % inputfile)
                    except:
                        log.exception("Error converting file %s." % inputfile)
                else:
                    log.debug("Ignoring file %s." % inputfile)
        if len(ignore) < 1:
            log.error("No valid files found for conversion in download, aborting.")
            sys.exit(1)
        if settings.output_dir:
            path = settings.output_dir
    else:
        log.info("Passing without conversion.")

    if settings.SAB['sb'].startswith(category):
        log.info("Passing %s directory to Sickbeard." % path)
        autoProcessTV.processEpisode(path, settings, nzb, pathMapping=path_mapping)
    elif settings.SAB['sonarr'].startswith(category):
        log.info("Passing %s directory to Sonarr." % path)
        sonarr.processEpisode(path, settings, importMode="Move", pathMapping=path_mapping)
    elif settings.SAB['radarr'].startswith(category):
        log.info("Passing %s directory to Radarr." % path)
        radarr.processMovie(path, settings, pathMapping=path_mapping)
    elif settings.SAB['sr'].startswith(category):
        log.info("Passing %s directory to Sickrage." % path)
        autoProcessTVSR.processEpisode(path, settings, nzb, pathMapping=path_mapping)
    elif [x for x in settings.SAB['bypass'] if x.startswith(category)]:
        log.info("Bypassing any further processing as per category.")
except:
    log.exception("Unexpected exception.")
    sys.exit(1)
