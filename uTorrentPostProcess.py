import os
import re
import sys
import shutil
from autoprocess import autoProcessTV, autoProcessMovie, autoProcessTVSR, sonarr, radarr
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4
import logging
from logging.config import fileConfig

fileConfig(os.path.join(os.path.dirname(sys.argv[0]), 'logging.ini'), defaults={'logfilename': os.path.join(os.path.dirname(sys.argv[0]), 'info.log').replace("\\", "/")})
log = logging.getLogger("uTorrentPostProcess")

log.info("uTorrent post processing started.")

# Args: %L %T %D %K %F %I Label, Tracker, Directory, single|multi, NameofFile(if single), InfoHash


def _authToken(session=None, host=None, username=None, password=None):
    auth = None
    if not session:
        session = requests.Session()
    response = session.get(host + "gui/token.html", auth=(username, password), verify=False, timeout=30)
    if response.status_code == 200:
        auth = re.search("<div.*?>(\S+)<\/div>", response.text).group(1)
    else:
        log.error("Authentication Failed - Status Code " + response.status_code + ".")

    return auth, session


def _sendRequest(session, host='http://localhost:8080/', username=None, password=None, params=None, files=None, fnct=None):
    try:
        response = session.post(host + "gui/", auth=(username, password), params=params, files=files, timeout=30)
    except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
        log.exception("Problem sending command " + fnct + " - " + str(e) + ".")
        return False

    if response.status_code == 200:
        log.debug("Request sent successfully - %s." % fnct)
        return True

    log.error("Problem sending command " + fnct + ", return code = " + str(response.status_code) + ".")
    return False

if len(sys.argv) < 6:
    log.error("Not enough command line parameters present, are you launching this from uTorrent?")
    log.error("#Args: %L %T %D %K %F %I %N Label, Tracker, Directory, single|multi, NameofFile(if single), InfoHash, Name")
    log.error("Length was %s" % str(len(sys.argv)))
    log.error(str(sys.argv[1:]))
    sys.exit()

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
path = str(sys.argv[3])
label = sys.argv[1].lower()
categories = [settings.uTorrent['cp'], settings.uTorrent['sb'], settings.uTorrent['sonarr'], settings.uTorrent['radarr'], settings.uTorrent['sr'], settings.uTorrent['bypass']]
torrent_hash = sys.argv[6]
try:
    name = sys.argv[7]
except:
    name = sys.argv[6]

log.debug("Path: %s." % path)
log.debug("Label: %s." % label)
log.debug("Categories: %s." % categories)
log.debug("Torrent hash: %s." % torrent_hash)
log.debug("Torrent name: %s." % name)

if label not in categories:
    log.error("No valid label detected.")
    sys.exit()

if len(categories) != len(set(categories)):
    log.error("Duplicate category detected. Category names must be unique.")
    sys.exit()

# Import requests
try:
    import requests
except ImportError:
    log.exception("Python module REQUESTS is required. Install with 'pip install requests' then try again.")
    sys.exit()

try:
    web_ui = settings.uTorrentWebUI
    log.debug("WebUI is true.")
except:
    log.debug("WebUI is false.")
    web_ui = False

delete_dir = False

# Run a uTorrent action before conversion.
if web_ui:
    session = requests.Session()
    if session:
        auth, session = _authToken(session, settings.uTorrentHost, settings.uTorrentUsername, settings.uTorrentPassword)
        if auth and settings.uTorrentActionBefore:
            params = {'token': auth, 'action': settings.uTorrentActionBefore, 'hash': torrent_hash}
            _sendRequest(session, settings.uTorrentHost, settings.uTorrentUsername, settings.uTorrentPassword, params, None, "Before Function")
            log.debug("Sending action %s to uTorrent" % settings.uTorrentActionBefore)

if settings.uTorrent['convert']:
    # Check for custom uTorrent output_dir
    if settings.uTorrent['output_dir']:
        settings.output_dir = settings.uTorrent['output_dir']
        log.debug("Overriding output_dir to %s." % settings.uTorrent['output_dir'])

    # Perform conversion.
    log.info("Performing conversion")
    settings.delete = False
    if not settings.output_dir:
        settings.output_dir = os.path.join(path, ("%s-convert" % name))
        if not os.path.exists(settings.output_dir):
            os.mkdir(settings.output_dir)
        delete_dir = settings.output_dir

    converter = MkvtoMp4(settings)

    if str(sys.argv[4]) == 'single':
        inputfile = os.path.join(path, str(sys.argv[5]))
        if MkvtoMp4(settings).validSource(inputfile):
            log.info("Processing file %s." % inputfile)
            try:
                output = converter.process(inputfile, reportProgress=True)
            except:
                log.exception("Error converting file %s." % inputfile)
        else:
            log.debug("Ignoring file %s." % inputfile)
    else:
        log.debug("Processing multiple files.")
        ignore = []
        for r, d, f in os.walk(path):
            for files in f:
                inputfile = os.path.join(r, files)
                if MkvtoMp4(settings).validSource(inputfile) and inputfile not in ignore:
                    log.info("Processing file %s." % inputfile)
                    try:
                        output = converter.process(inputfile)
                        ignore.append(output['output'])
                    except:
                        log.exception("Error converting file %s." % inputfile)
                else:
                    log.debug("Ignoring file %s." % inputfile)

    path = converter.output_dir
else:
    newpath = os.path.join(path, name)
    if not os.path.exists(newpath):
        os.mkdir(newpath)
        log.debug("Creating temporary directory %s" % newpath)
    if str(sys.argv[4]) == 'single':
        inputfile = os.path.join(path, str(sys.argv[5]))
        shutil.copy(inputfile, newpath)
        log.debug("Copying %s to %s" % (inputfile, newpath))
    else:
        for r, d, f in os.walk(path):
            for files in f:
                inputfile = os.path.join(r, files)
                shutil.copy(inputfile, newpath)
                log.debug("Copying %s to %s" % (inputfile, newpath))
    path = newpath
    delete_dir = newpath

if label == categories[0]:
    log.info("Passing %s directory to Couch Potato." % path)
    autoProcessMovie.process(path, settings)
elif label == categories[1]:
    log.info("Passing %s directory to Sickbeard." % path)
    autoProcessTV.processEpisode(path, settings)
elif label == categories[2]:
    log.info("Passing %s directory to Sonarr." % path)
    sonarr.processEpisode(path, settings)
elif label == categories[3]:
    log.info("Passing %s directory to Radarr." % path)
    radarr.processMovie(path, settings)
elif label == categories[4]:
    log.info("Passing %s directory to Sickrage." % path)
    autoProcessTVSR.processEpisode(path, settings)
elif label == categories[5]:
    log.info("Bypassing any further processing as per category.")

# Run a uTorrent action after conversion.
if web_ui:
    if session and auth and settings.uTorrentActionAfter:
        params = {'token': auth, 'action': settings.uTorrentActionAfter, 'hash': torrent_hash}
        _sendRequest(session, settings.uTorrentHost, settings.uTorrentUsername, settings.uTorrentPassword, params, None, "After Function")
        log.debug("Sending action %s to uTorrent" % settings.uTorrentActionAfter)

if delete_dir:
    if os.path.exists(delete_dir):
        try:
            os.rmdir(delete_dir)
            log.debug("Successfully removed tempoary directory %s." % delete_dir)
        except:
            log.exception("Unable to delete temporary directory")

sys.exit()
