#!/usr/bin/env python

import os
import sys
import autoProcessTV, autoProcessMovie
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4

# SABnzbd argv:
# 1 The final directory of the job (full path)
# 2 The original name of the NZB file
# 3 Clean version of the job name (no path info and ".nzb" removed)
# 4 Indexer's report number (if supported)
# 5 User-defined category
# 6 Group that the NZB was posted in e.g. alt.binaries.x
# 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
categories = [settings.SAB['sb'], settings.SAB['cp'], settings.SAB['sonarr'], settings.SAB['bypass']]
category = str(sys.argv[5]).lower()

if category.lower() not in categories:
    print "Error, no valid category detected"
    sys.exit()

path = str(sys.argv[1])
nzb = str(sys.argv[2])

if settings.SAB['convert']:
    print "Converting before passing"
    converter = MkvtoMp4(settings)
    converter.output_dir = None
    for r, d, f in os.walk(path):
        for files in f:
            inputfile = os.path.join(r, files)
            if MkvtoMp4(settings).validSource(inputfile):
                try:
                	print "Valid file detected: " + inputfile
                except:
                	print "Valid file detected"
                converter.process(inputfile)
else:
    print "Passing without conversion"

# Send to Sickbeard
if (category == categories[0]):
    if len(sys.argv) < 2:
        print "No folder supplied - is this being called from SABnzbd?"
        sys.exit()
    elif len(sys.argv) >= 3:
        autoProcessTV.processEpisode(path, settings, nzb)
    else:
        autoProcessTV.processEpisode(path, settings)

# Send to CouchPotato        
elif (category == categories[1]):
    autoProcessMovie.process(path, settings, nzb, sys.argv[7])
# Send to Sonarr
elif (category == categories[2]):
    # Import requests
    try:
        import requests
    except ImportError:
        print "[ERROR] Python module REQUESTS is required. Install with 'pip install requests' then try again."
        sys.exit()
elif (category == categories[3]):
    print "Bypassing any further processing as per category"

    host=settings.Sonarr['host']
    port=settings.Sonarr['port']
    apikey = settings.Sonarr['apikey']
    if apikey == '':
        print "[WARNING] Your Sonarr API Key can not be blank. Update autoProcess.ini"
    try:
        ssl=int(settings.Sonarr['ssl'])
    except:
        ssl=0
    if ssl:
        protocol="https://"
    else:
        protocol="http://"
    url = protocol+host+":"+port+"/api/command"
    payload = {'name': 'downloadedepisodesscan','path': path}
    print "[INFO] Requesting Sonarr to scan folder '"+path+"'"
    headers = {'X-Api-Key': apikey}
    try:
        r = requests.post(url, data=json.dumps(payload), headers=headers)
        rstate = r.json()
        print "[INFO] Sonarr responds as "+rstate['state']+"."
    except:
        print "[WARNING] Update to Sonarr failed, check if Sonarr is running, autoProcess.ini for errors, or check install of python modules requests."
    