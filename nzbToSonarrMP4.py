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

import os, sys, re, requests, json
sys.path.append(os.environ['NZBPO_MP4_FOLDER'])
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4

# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    print "[INFO] Script triggered from NZBGet (11.0 or later)."

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

    # All checks done, now launching the script.
    #print os.environ['NZBPO_MP4_FOLDER']+"autoProcess.ini"
    settings = ReadSettings(os.path.dirname(sys.argv[0]), os.environ['NZBPO_MP4_FOLDER']+"autoProcess.ini")

    path = os.environ['NZBPP_DIRECTORY']
    converter = MkvtoMp4(settings)
    converter.output_dir = None
    for r, d, f in os.walk(path):
        for files in f:
            inputfile = os.path.join(r, files)
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
                    except:
                        print "[WARNING] File conversion failed"
                        raise
                        sys.exit(POSTPROCESS_ERROR)
            #else:
            #	print "Possible sample file detected: " + inputfile + " skipping file"

    #Send Folder Scan command to Sonarr
    #Example:curl http://localhost:8989/api/command -X POST -d '{"name": "downloadedepisodesscan"}' --header "X-Api-Key:XXXXXXXXXXX"
    host=settings.Sonarr['host']
    port=settings.Sonarr['port']
    apikey = settings.Sonarr['apikey']
    try:
        ssl=int(settings.Sonarr['ssl'])
    except (ConfigParser.NoOptionError,ValueError):
        ssl=0
    if ssl:
        protocol="https://"
    else:
        protocol="http://"
    url = protocol+host+":"+port+"/api/command"
    payload = {'name': 'downloadedepisodesscan','path': path}
    headers = {'X-Api-Key': apikey}
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    rstate = r.json()
    print "[INFO] Sonarr update is "+rstate['state']+"."
    
    sys.exit(POSTPROCESS_SUCCESS)

else:
    print "[ERROR] This script can only be called from NZBGet (11.0 or later)."
    sys.exit(0)
