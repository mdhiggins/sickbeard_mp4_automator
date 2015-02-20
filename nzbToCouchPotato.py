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

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import os
import sys
import autoProcessMovie

#Exit if missing requests module
try:
    import requests
except ImportError:
    pass
    print "[ERROR] Python module REQUESTS is required. Install with 'pip install requests' then try again."
    sys.exit(0)

#Sanity checks for path string
MP4folder = os.environ['NZBPO_MP4_FOLDER'].replace('"','')
MP4folder = MP4folder.replace("'","")
if not(MP4folder.endswith("/")):
    MP4folder += "/"
#DEBUG#print MP4folder+" the original is "+os.environ['NZBPO_MP4_FOLDER']

if MP4folder != os.environ['NZBPO_MP4_FOLDER']:
    print "[WARNING] MP4 Folder path option is in an invalid format but was corrected."

sys.path.append(MP4folder)
try:
    from readSettings import ReadSettings
    from mkvtomp4 import MkvtoMp4
except ImportError:
    pass
    print "[ERROR] Wrong path to sickbeard_mp4_automator: "+os.environ['NZBPO_MP4_FOLDER']
    sys.exit(0)

if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    print "[INFO] Script triggered from NZBGet (11.0 or later)."

    path = os.environ['NZBPP_DIRECTORY']
	nzb = os.environ['NZBPP_NZBFILENAME']

    # NZBGet argv: all passed as environment variables.
    clientAgent = "nzbget"
    # Exit codes used by NZBGet
    POSTPROCESS_PARCHECK=92
    POSTPROCESS_SUCCESS=93
    POSTPROCESS_ERROR=94
    POSTPROCESS_NONE=95

    # Check nzbget.conf options
    status = 0

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

	print "Script triggered from NZBGet, starting autoProcessMovie..."
	autoProcessMovie.process(path, nzb, status)

else:
    print "[ERROR] This script can only be called from NZBGet (11.0 or later)."
    sys.exit(0)
