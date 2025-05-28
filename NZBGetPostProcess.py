#!/usr/bin/env python3
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Converts files and passes them to Sonarr for further processing.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

# Change to full path to MP4 Automator folder. No quotes and a trailing /
#MP4_FOLDER=~/sickbeard_mp4_automator/

# Convert file before passing to destination (True, False)
#SHOULDCONVERT=False

# Category for Sonarr
#SONARR_CAT=Sonarr

# Category for Radarr
#RADARR_CAT=Radarr

# Category for Sickbeard
#SICKBEARD_CAT=Sickbeard

# Category for Sickrage
#SICKRAGE_CAT=Sickrage

# Category for bypassing any further processing but still converting
#BYPASS_CAT=Bypass

# Custom output_directory setting
#OUTPUT_DIR=

# Custom path mapping setting
#PATH_MAPPING=

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import os
import sys
import re
import json
import traceback

# Sanity checks for path string
MP4folder = os.environ['NZBPO_MP4_FOLDER'].strip()
MP4folder = MP4folder.replace('"', '')
MP4folder = MP4folder.replace("'", "")
MP4folder = MP4folder.replace("\\", "/")
if not(MP4folder.endswith("/")):
    MP4folder += "/"
#DEBUG#print MP4folder+" the original is "+os.environ['NZBPO_MP4_FOLDER']

output_dir = None
if 'NZBPO_OUTPUT_DIR' in os.environ:
    output_dir = os.environ['NZBPO_OUTPUT_DIR'].strip()
    if len(output_dir) > 0:
        output_dir = output_dir.replace('"', '')
        output_dir = output_dir.replace("'", "")
        output_dir = output_dir.replace("\\", "/")
        if not(output_dir.endswith("/")):
            output_dir += "/"
        #DEBUG#print Overriding output directory

path_mapping = {}
if 'NZBPO_PATH_MAPPING' in os.environ:
    pathpairs = os.environ['NZBPO_PATH_MAPPING'].split(",")
    pathpairs = [x.strip() for x in pathpairs]
    for listitem in pathpairs:
        split = listitem.split(":")
        if len(split) > 1:
            path_mapping[split[0].strip()] = split[1].strip()

sys.path.insert(0, MP4folder)
try:
    from resources.readsettings import ReadSettings
    from resources.mediaprocessor import MediaProcessor
    from resources.log import getLogger
    from autoprocess import autoProcessTV, autoProcessTVSR, sonarr, radarr
except ImportError:
    print("[ERROR] Wrong path to sickbeard_mp4_automator: " + os.environ['NZBPO_MP4_FOLDER'])
    print("[ERROR] %s" % traceback.print_exc())
    sys.exit(1)

# Setup Logging
log = getLogger("NZBGetPostProcess", MP4folder)

# Determine if conversion will take place
shouldConvert = (os.environ['NZBPO_SHOULDCONVERT'].lower() in ("yes", "true", "t", "1"))


def progressOutput(timecode, debug):
    log.info(timecode)
    log.debug(debug)


if 'NZBOP_SCRIPTDIR' in os.environ and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    log.info("Script triggered from NZBGet (11.0 or later).")

    path = os.environ['NZBPP_DIRECTORY']  # Path to NZB directory
    nzb = os.environ['NZBPP_NZBFILENAME']  # Original NZB name
    category = os.environ['NZBPP_CATEGORY'].lower().strip()  # NZB Category to determine destination
    #DEBUG#print "Category is %s." % category

    sonarrcat = os.environ['NZBPO_SONARR_CAT'].lower().strip()
    radarrcat = os.environ['NZBPO_RADARR_CAT'].lower().strip()
    sickbeardcat = os.environ['NZBPO_SICKBEARD_CAT'].lower().strip()
    sickragecat = os.environ['NZBPO_SICKRAGE_CAT'].lower().strip()
    bypass = os.environ['NZBPO_BYPASS_CAT'].lower().strip()

    categories = [sickbeardcat, sonarrcat, radarrcat, sickragecat] + bypass

    log.debug("Path: %s" % path)
    log.debug("NZB: %s" % nzb)
    log.debug("Category: %s" % category)
    log.debug("Categories: %s" % categories)

    # NZBGet argv: all passed as environment variables.
    clientAgent = "nzbget"
    # Exit codes used by NZBGet
    POSTPROCESS_PARCHECK = 92
    POSTPROCESS_SUCCESS = 93
    POSTPROCESS_ERROR = 94
    POSTPROCESS_NONE = 95

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != 'yes':
        log.error("Please enable option \"Unpack\" in nzbget configuration file, exiting.")
        sys.exit(POSTPROCESS_NONE)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        log.error("Par-check successful, but Par-repair disabled, exiting")
        sys.exit(POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1':
        log.error("Par-check failed, setting status \"failed\".")
        status = 1
        sys.exit(POSTPROCESS_NONE)

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        log.error("Unpack failed, setting status \"failed\".")
        status = 1
        sys.exit(POSTPROCESS_NONE)

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] != '2':
        # Unpack is disabled or was skipped due to nzb-file properties or due to errors during par-check

        for dirpath, dirnames, filenames in os.walk(os.environ['NZBPP_DIRECTORY']):
            for file in filenames:
                fileExtension = os.path.splitext(file)[1]

                if fileExtension in ['.par2']:
                    log.error("Post-Process: Unpack skipped and par-check skipped (although par2-files exist), setting status \"failed\".")
                    status = 1
                    break

        if os.path.isfile(os.path.join(os.environ['NZBPP_DIRECTORY'], "_brokenlog.txt")) and not status == 1:
            log.error("Post-Process: _brokenlog.txt exists, download is probably damaged, exiting.")
            status = 1

        if not status == 1:
            log.error("Neither par2-files found, _brokenlog.txt doesn't exist, considering download successful.")

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        log.error("Post-Process: Nothing to post-process: destination directory ", os.environ['NZBPP_DIRECTORY'], "doesn't exist.")
        status = 1
        sys.exit(POSTPROCESS_NONE)

    # Make sure one of the appropriate categories is set
    if len([x for x in categories if x.startswith(category)]) < 1:
        log.error("Post-Process: No valid category detected. Category was %s." % (category))
        status = 1
        sys.exit(POSTPROCESS_NONE)

    # Make sure there are no duplicate categories
    if len(categories) != len(set(categories)):
        log.error("Duplicate category detected. Category names must be unique.")
        status = 1
        sys.exit(POSTPROCESS_NONE)

    # All checks done, now launching the script.
    settings = ReadSettings(MP4folder)

    if shouldConvert:
        if output_dir:
            settings.output_dir = output_dir
        mp = MediaProcessor(settings, logger=log)
        ignore = []
        for r, d, f in os.walk(path):
            for files in f:
                inputfile = os.path.join(r, files)
                #DEBUG#print inputfile
                info = mp.isValidSource(inputfile)
                if info and inputfile not in ignore:
                    log.info("Processing file %s." % inputfile)
                    try:
                        output = mp.process(inputfile, info=info, reportProgress=True, progressOutput=progressOutput)
                        if output and output.get('output'):
                            log.info("Successfully processed %s." % inputfile)
                            ignore.append(output.get('output'))
                        else:
                            log.error("Converting file failed %s." % inputfile)
                    except:
                        log.exception("File processing failed.")
                else:
                    log.debug("Ignoring file %s." % inputfile)
        if len(ignore) < 1:
            log.error("No valid files for processing found, aborting.")
            sys.exit(POSTPROCESS_ERROR)
        if settings.output_dir:
            path = settings.output_dir
    if (sickbeardcat.startswith(category)):
        #DEBUG#print "Sickbeard Processing Activated"
        autoProcessTV.processEpisode(path, settings, nzb, pathMapping=path_mapping)
        sys.exit(POSTPROCESS_SUCCESS)
    elif (sonarrcat.startswith(category)):
        #DEBUG#print "Sonarr Processing Activated"
        success = sonarr.processEpisode(path, settings, True, importMode="Move", pathMapping=path_mapping)
        if success:
            sys.exit(POSTPROCESS_SUCCESS)
        else:
            sys.exit(POSTPROCESS_NONE)
    elif (radarrcat.startswith(category)):
        #DEBUG#print "Radarr Processing Activated"
        success = radarr.processMovie(path, settings, True, pathMapping=path_mapping)
        if success:
            sys.exit(POSTPROCESS_SUCCESS)
        else:
            sys.exit(POSTPROCESS_NONE)
    elif (sickragecat.startswith(category)):
        #DEBUG#print "Sickrage Processing Activated"
        autoProcessTVSR.processEpisode(path, settings, nzb, pathMapping=path_mapping)
        sys.exit(POSTPROCESS_SUCCESS)
    elif [x for x in bypass if x.startswith(category)]:
        #DEBUG#print "Bypass Further Processing"
        sys.exit(POSTPROCESS_NONE)

else:
    log.error("This script can only be called from NZBGet (11.0 or later).")
    sys.exit(1)
