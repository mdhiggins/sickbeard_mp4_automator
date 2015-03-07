#!/usr/bin/env python

import os
import sys
from autoprocess import autoProcessTV, autoProcessMovie, autoProcessTVSR
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4
from deluge import DelugeClient
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=os.path.join(os.path.dirname(sys.argv[0]), "info.log"),
                    filemode='w')
log = logging.getLogger("delugePostProcess")
log.info("Deluge post processing started.")

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
categories = [settings.deluge['sb'], settings.deluge['cp'], settings.deluge['sonarr'], settings.deluge['sr'], settings.deluge['bypass']]

if len(sys.argv) < 4:
    log.error("Not enough command line parameters present, are you launching this from deluge?")
    sys.exit()

path = str(sys.argv[3])
torrent_name = str(sys.argv[2])
torrent_id = str(sys.argv[1])

log.debug("Path: %s." % path)
log.debug("Torrent: %s." % torrent_name)
log.debug("Hash: %s." % torrent_id)

client = DelugeClient()
client.connect(host=settings.deluge['host'], port=int(settings.deluge['port']), username=settings.deluge['user'], password=settings.deluge['pass'])

torrent_files = client.core.get_torrent_status(torrent_id, ['files']).get()['files']

files = []
log.debug("List of files in torrent:")
for contents in torrent_files:
    files.append(contents['path'])
    log.debug(contents['path'])

try:
    category = client.core.get_torrent_status(torrent_id, ['label']).get()['label'].lower()
    log.debug("Category: %s" % category)
except Exception as e:
    log.exeption("Unable to connect to deluge to retrieve category.")
    sys.exit()

if category.lower() not in categories:
    log.error("No valid category detected.")
    sys.exit()

if len(categories) != len(set(categories)):
    log.error("Duplicate category detected. Category names must be unique.")
    sys.exit()

if settings.deluge['convert']:
    # Perform conversion.
    settings.delete = False
    if not settings.output_dir:
        settings.output_dir = os.path.join(path, torrent_id)
        if not os.path.exists(settings.output_dir):
            os.mkdir(settings.output_dir)
        delete_dir = settings.output_dir

    converter = MkvtoMp4(settings)

    for filename in files:
        inputfile = os.path.join(path, filename)
        log.info("Converting file %s at location %s." % (inputfile, settings.output_dir))
        if MkvtoMp4(settings).validSource(inputfile):
            converter.process(inputfile, reportProgress=True)

    path = converter.output_dir
else:
    newpath = os.path.join(path, torrent_id)
    if not os.path.exists(newpath):
        os.mkdir(newpath)
    for filename in files:
        inputfile = os.path.join(path, filename)
        log.info("Copying file %s to %s." % (inputfile, newpath))
        shutil.copy(inputfile, newpath)
    path = newpath
    delete_dir = newpath
    
# Send to Sickbeard
if (category == categories[0]):
    log.info("Passing %s directory to Sickbeard." % path)
    autoProcessTV.processEpisode(path, settings)
# Send to CouchPotato        
elif (category == categories[1]):
    log.info("Passing %s directory to CouchPotato." % path)
    autoProcessMovie.process(path, settings)
# Send to Sonarr
elif (category == categories[2]):
    log.info("Passing %s directory to Sonarr." % path)
    # Import requests
    try:
        import requests
    except ImportError:
        log.exception("Python module REQUESTS is required. Install with 'pip install requests' then try again.")
        sys.exit()

    host=settings.Sonarr['host']
    port=settings.Sonarr['port']
    apikey = settings.Sonarr['apikey']
    if apikey == '':
        log.error("Your Sonarr API Key can not be blank. Update autoProcess.ini")
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
    log.info("Requesting Sonarr to scan folder '"+path+"'")
    headers = {'X-Api-Key': apikey}
    try:
        r = requests.post(url, data=json.dumps(payload), headers=headers)
        rstate = r.json()
        log.info("Sonarr responds as "+rstate['state']+".")
    except:
        log.error("Update to Sonarr failed, check if Sonarr is running, autoProcess.ini for errors, or check install of python modules requests.")
elif (category == categories[3]):
    log.info("Passing %s directory to Sickrage." % path)
    autoProcessTVSR.processEpisode(path, settings)
elif (category == categories[4]):
    log.info("Bypassing any further processing as per category.")

if delete_dir:
    try:
        os.rmdir(delete_dir)
        log.debug("Successfully removed tempoary directory %s." % delete_dir)
    except:
        log.exception("Unable to delete temporary directory.")
    
