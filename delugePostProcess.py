#!/usr/bin/env python

import os
import sys
from autoprocess import autoProcessTV, autoProcessMovie, autoProcessTVSR
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4
from deluge import DelugeClient

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
categories = [settings.deluge['sb'], settings.deluge['cp'], settings.deluge['sonarr'], settings.deluge['sr'], settings.deluge['bypass']]

path = str(sys.argv[3])
torrent_name = str(sys.argv[2])
torrent_id = str(sys.argv[1])

client = DelugeClient()
client.connect(host=settings.deluge['host'], port=settings.deluge['port'], username=settings.deluge['host'],
                                 password=settings.deluge['pass'])

try:
    category = client.core.get_torrent_status(torrent_id, ['label']).get()['label'].lower()
except Exception as e:
    print "Error, unable to connect to deluge to retrieve category"
    print e

if category.lower() not in categories:
    print "Error, no valid category detected"
    print "Category '%s' not in:" % category
    print categories
    sys.exit()

if len(categories) != len(set(categories)):
    print "Error, duplicate category detected. Category names must be unique"
    print categories
    sys.exit()

# Convert if needed
if settings.deluge['convert']:
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
    autoProcessTV.processEpisode(path, settings)
# Send to CouchPotato        
elif (category == categories[1]):
    print "Passing to CouchPotato"
    autoProcessMovie.process(path, settings)
# Send to Sonarr
elif (category == categories[2]):
    print "Passing to Sonarr"
    # Import requests
    try:
        import requests
    except ImportError:
        print "[ERROR] Python module REQUESTS is required. Install with 'pip install requests' then try again."
        sys.exit()

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
elif (category == categories[3]):
    print "Passing to Sickrage"
    autoProcessTVSR.processEpisode(path, settings)
elif (category == categories[4]):
    print "Bypassing any further processing as per category"
    