#!/usr/bin/env python
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

# Category for Couchpotato
#CP_CAT=Couchpotato

# Category for Sonarr
#SONARR_CAT=Sonarr

# Category for Sickbeard
#SICKBEARD_CAT=Sickbeard

# Category for Sickrage
#SICKRAGE_CAT=Sickrage

# Category for bypassing any further processing but still converting
#BYPASS_CAT=Bypass

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import os, sys, re, json


#Sanity checks for path string
MP4folder = os.environ['NZBPO_MP4_FOLDER'].replace('"','')
MP4folder = MP4folder.replace("'","")
if not(MP4folder.endswith("/")) and os.name != 'nt':
    MP4folder += "/"
if not MP4folder.endswith("\\") and os.name == 'nt':
    MP4folder += "\\"
#DEBUG#print MP4folder+" the original is "+os.environ['NZBPO_MP4_FOLDER']

if MP4folder != os.environ['NZBPO_MP4_FOLDER']:
    print "[WARNING] MP4 Folder path option is in an invalid format but was corrected."

sys.path.append(MP4folder)
try:
    from readSettings import ReadSettings
    from mkvtomp4 import MkvtoMp4
    from autoprocess import autoProcessMovie, autoProcessTV, autoProcessTVSR, sonarr
except ImportError:
    pass
    print "[ERROR] Wrong path to sickbeard_mp4_automator: "+os.environ['NZBPO_MP4_FOLDER']
    sys.exit(0)

#Determine if conversion will take place
shouldConvert = (os.environ['NZBPO_SHOULDCONVERT'].lower() in ("yes", "true", "t", "1"))

if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    print "[INFO] Script triggered from NZBGet (11.0 or later)."

    path = os.environ['NZBPP_DIRECTORY'] # Path to NZB directory
    nzb = os.environ['NZBPP_NZBFILENAME'] # Original NZB name
    category = os.environ['NZBPP_CATEGORY'] # NZB Category to determine destination
    #DEBUG#print "Category is %s" % category
    
    couchcat = os.environ['NZBPO_CP_CAT'].lower()
    sonarrcat = os.environ['NZBPO_SONARR_CAT'].lower()
    sickbeardcat = os.environ['NZBPO_SICKBEARD_CAT'].lower()
    sickragecat = os.environ['NZBPO_SICKRAGE_CAT'].lower()
    bypass = os.environ['NZBPO_BYPASS_CAT'].lower()
    
    categories = [sickbeardcat, couchcat, sonarrcat, sickragecat, bypass]
    
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
        print "[INFO] Please enable option \"Unpack\" in nzbget configuration file, exiting"
        sys.exit(POSTPROCESS_NONE)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        print "[INFO] Par-check successful, but Par-repair disabled, exiting"
        sys.exit(POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1':
        print "[INFO] Par-check failed, setting status \"failed\""
        status = 1
        sys.exit(POSTPROCESS_NONE)

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        print "[INFO] Unpack failed, setting status \"failed\""
        status = 1
        sys.exit(POSTPROCESS_NONE)

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] != '2':
        # Unpack is disabled or was skipped due to nzb-file properties or due to errors during par-check

        for dirpath, dirnames, filenames in os.walk(os.environ['NZBPP_DIRECTORY']):
            for file in filenames:
                fileExtension = os.path.splitext(file)[1]

                if fileExtension in ['.par2']:
                    print "[INFO] Post-Process: Unpack skipped and par-check skipped (although par2-files exist), setting status \"failed\"g"
                    status = 1
                    break

        if os.path.isfile(os.path.join(os.environ['NZBPP_DIRECTORY'], "_brokenlog.txt")) and not status == 1:
            print "[INFO] Post-Process: _brokenlog.txt exists, download is probably damaged, exiting"
            status = 1

        if not status == 1:
            print "[INFO] Neither par2-files found, _brokenlog.txt doesn't exist, considering download successful"

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        print "[INFO] Post-Process: Nothing to post-process: destination directory ", os.environ['NZBPP_DIRECTORY'], "doesn't exist"
        status = 1
        sys.exit(POSTPROCESS_NONE)

    # Make sure one of the appropriate categories is set
    if category.lower() not in categories:
        print "[ERROR] Post-Process: No valid category detected. Category was %s." % (category)
        status = 1
        sys.exit(POSTPROCESS_NONE)

    # Make sure there are no duplicate categories
    if len(categories) != len(set(categories)):
        print "[ERROR] Duplicate category detected. Category names must be unique"
        status = 1
        sys.exit(POSTPROCESS_NONE)

    # All checks done, now launching the script.
    settings = ReadSettings(MP4folder, "autoProcess.ini")

    if shouldConvert:
        converted = 0
        attempted = 0
        converter = MkvtoMp4(settings)
        converter.output_dir = None
        for r, d, f in os.walk(path):
            for files in f:
                attempted += 1
                inputfile = os.path.join(r, files)
                #DEBUG#print inputfile
                #Ignores files under 50MB
                if os.path.getsize(inputfile) > 50000000:
                    if MkvtoMp4(settings).validSource(inputfile):
                        try:
                            print "[INFO] Valid file detected: " + inputfile
                        except:
                            print "[INFO] Valid file detected"
                        try:
                            converter.process(inputfile)
                            print "[INFO] Successfully converted!"
                            converted += 1
                        except:
                            print "[WARNING] File conversion failed!"
        #DEBUG#print "%d of %d files converted", (converted, attempted)

    if (category.lower() == categories[0]):
        #DEBUG#print "Sickbeard Processing Activated"
        autoProcessTV.processEpisode(path, settings, nzb)
        sys.exit(POSTPROCESS_SUCCESS)
    elif (category.lower() == categories[1]):
        #DEBUG#print "CouchPotato Processing Activated"
        autoProcessMovie.process(path, settings, nzb, status)
        sys.exit(POSTPROCESS_SUCCESS)
    elif (category.lower() == categories[2]):
        success = sonarr.processEpisode(path, settings, True)
        if success:
            sys.exit(POSTPROCESS_SUCCESS)
        else:
            sys.exit(POSTPROCESS_ERROR)
    elif (category.lower() == categories[3]):
        #DEBUG#print "Sickrage Processing Activated"
        autoProcessTVSR.processEpisode(path, settings, nzb)
    elif (category.lower() == categories[4]):
        #DEBUG#print "Bypass Further Processing"
        pass

else:
    print "[ERROR] This script can only be called from NZBGet (11.0 or later)."
    sys.exit(0)
