#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Converts files and passes them to Sonarr/CouchPotato/etc for further processing.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

# Change to full path to MP4 Automator folder. No quotes and a trailing /
#MP4_FOLDER=~/sickbeard_mp4_automator/

# Convert file before passing to destination (True, False)
#SHOULDCONVERT=False

# Comma separated list of categories for Couchpotato
#CP_CAT=Couchpotato

# Comma separated list of categories for Sonarr
#SONARR_CAT=Sonarr

# Comma separated list of categories for Sickbeard
#SICKBEARD_CAT=Sickbeard

# Comma separated list of categories for Sickrage
#SICKRAGE_CAT=Sickrage

# Comma separated list of categories for bypassing any further processing but still converting
#BYPASS_CAT=Bypass

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import os, sys, re, json


#Sanity checks for path string
MP4folder = os.environ['NZBPO_MP4_FOLDER'].strip()
MP4folder = MP4folder.replace('"','')
MP4folder = MP4folder.replace("'","")
MP4folder = MP4folder.replace("\\","/")
if not(MP4folder.endswith("/")):
    MP4folder += "/"
#DEBUG#print MP4folder+" the original is "+os.environ['NZBPO_MP4_FOLDER']

sys.path.append(MP4folder)
try:
    from readSettings import ReadSettings
    from mkvtomp4 import MkvtoMp4
    from autoprocess import autoProcessMovie, autoProcessTV, autoProcessTVSR, sonarr
    import logging
    from logging.config import fileConfig
except ImportError:
    pass
    print "[ERROR] Wrong path to sickbeard_mp4_automator: "+os.environ['NZBPO_MP4_FOLDER']
    sys.exit(0)

# Setup Logging
fileConfig(os.path.join(MP4folder, 'logging.ini'), defaults={'logfilename': os.path.join(MP4folder, 'info.log')})
log = logging.getLogger("NZBGetPostProcess")

#Determine if conversion will take place
shouldConvert = (os.environ['NZBPO_SHOULDCONVERT'].lower() in ("yes", "true", "t", "1"))

if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    log.info("Script triggered from NZBGet (11.0 or later).")

    path = os.environ['NZBPP_DIRECTORY'] # Path to NZB directory
    nzb = os.environ['NZBPP_NZBFILENAME'] # Original NZB name
    category = os.environ['NZBPP_CATEGORY'] # NZB Category to determine destination
    #DEBUG#print "Category is %s." % category

    couchcat = [x.strip() for x in os.environ['NZBPO_CP_CAT'].lower().split(',')]
    sonarrcat = [x.strip() for x in os.environ['NZBPO_SONARR_CAT'].lower().split(',')]
    sickbeardcat = [x.strip() for x in os.environ['NZBPO_SICKBEARD_CAT'].lower().split(',')]
    sickragecat = [x.strip() for x in os.environ['NZBPO_SICKRAGE_CAT'].lower().split(',')]
    bypass = [x.strip() for x in os.environ['NZBPO_BYPASS_CAT'].lower().split(',')]

    categories = sickbeardcat + couchcat + sonarrcat + sickragecat + bypass

    log.debug("Path: %s" % path)
    log.debug("NZB: %s" % nzb)
    log.debug("Category: %s" % category)
    log.debug("Categories: %s" % categories)

    # NZBGet argv: all passed as environment variables.
    clientAgent = "nzbget"
    # Exit codes used by NZBGet
    POSTPROCESS_PARCHECK=92
    POSTPROCESS_SUCCESS=93
    POSTPROCESS_ERROR=94
    POSTPROCESS_NONE=95

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
    if category.lower() not in categories:
        log.error("Post-Process: No valid category detected. Category was %s." % (category))
        status = 1
        sys.exit(POSTPROCESS_NONE)

    # Make sure there are no duplicate categories
    if len(categories) != len(set(categories)):
        log.error("Duplicate category detected. Category names must be unique.")
        status = 1
        sys.exit(POSTPROCESS_NONE)

    # All checks done, now launching the script.
    settings = ReadSettings(MP4folder, "autoProcess.ini")

    if shouldConvert:
        converter = MkvtoMp4(settings, logger=log)
        converter.output_dir = None
        for r, d, f in os.walk(path):
            for files in f:
                inputfile = os.path.join(r, files)
                #DEBUG#print inputfile
                #Ignores files under 50MB
                if os.path.getsize(inputfile) > 50000000:
                    if MkvtoMp4(settings, logger=log).validSource(inputfile):
                        try:
                            output = converter.process(inputfile)
                            log.info("Successfully processed %s." % inputfile)
                            if (category.lower() in sonarrcat and settings.relocate_moov):
                                log.debug("Performing QTFS move because video was converted and Sonarr has no post processing.")
                                converter.QTFS(output['output'])
                        except:
                            log.warning("File processing failed.")

    if (category.lower() in sickbeardcat):
        #DEBUG#print "Sickbeard Processing Activated"
        autoProcessTV.processEpisode(path, settings, nzb)
        sys.exit(POSTPROCESS_SUCCESS)
    elif (category.lower() in couchcat):
        #DEBUG#print "CouchPotato Processing Activated"
        autoProcessMovie.process(path, settings, nzb, status)
        sys.exit(POSTPROCESS_SUCCESS)
    elif (category.lower() in sonarrcat):
        success = sonarr.processEpisode(path, settings, True)
        if success:
            sys.exit(POSTPROCESS_SUCCESS)
        else:
            sys.exit(POSTPROCESS_ERROR)
    elif (category.lower() in sickragecat):
        #DEBUG#print "Sickrage Processing Activated"
        autoProcessTVSR.processEpisode(path, settings, nzb)
        sys.exit(POSTPROCESS_SUCCESS)
    elif (category.lower() in bypass):
        #DEBUG#print "Bypass Further Processing"
        sys.exit(POSTPROCESS_NONE)

else:
    log.error("This script can only be called from NZBGet (11.0 or later).")
    sys.exit(0)
