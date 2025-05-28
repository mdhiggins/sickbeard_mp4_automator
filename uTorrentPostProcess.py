import os
import re
import sys
import shutil
from autoprocess import autoProcessTV, autoProcessTVSR, sonarr, radarr
from resources.log import getLogger
from resources.readsettings import ReadSettings
from resources.mediaprocessor import MediaProcessor

log = getLogger("uTorrentPostProcess")

log.info("uTorrent post processing started.")

# Args: %L %T %D %K %F %I Label, Tracker, Directory, single|multi, NameofFile(if single), InfoHash


def getHost(host='localhost', port=8080, ssl=False):
    protocol = "https://" if ssl else "http://"
    return protocol + host + ":" + str(port) + "/"


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
    except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError):
        log.exception("Problem sending command")
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
    sys.exit(1)

try:
    settings = ReadSettings()
    path = str(sys.argv[3])
    label = sys.argv[1].lower().strip()
    kind = sys.argv[4].lower().strip()
    filename = sys.argv[5].strip()
    categories = [settings.uTorrent['sb'], settings.uTorrent['sonarr'], settings.uTorrent['radarr'], settings.uTorrent['sr']] + settings.uTorrent['bypass']
    torrent_hash = sys.argv[6]
    try:
        name = sys.argv[7]
    except:
        name = sys.argv[6]
    path_mapping = settings.uTorrent['path-mapping']

    log.debug("Path: %s." % path)
    log.debug("Label: %s." % label)
    log.debug("Categories: %s." % categories)
    log.debug("Torrent hash: %s." % torrent_hash)
    log.debug("Torrent name: %s." % name)
    log.debug("Kind: %s." % kind)
    log.debug("Filename: %s." % filename)

    if not label or len([x for x in categories if x.startswith(label)]) < 1:
        log.error("No valid label detected.")
        sys.exit(1)

    if len(categories) != len(set(categories)):
        log.error("Duplicate category detected. Category names must be unique.")
        sys.exit(1)

    # Import requests
    try:
        import requests
    except ImportError:
        log.exception("Python module REQUESTS is required. Install with 'pip install requests' then try again.")
        sys.exit(1)

    try:
        web_ui = settings.uTorrent['webui']
        log.debug("WebUI is true.")
    except:
        log.debug("WebUI is false.")
        web_ui = False

    delete_dir = False
    host = getHost(settings.uTorrent['host'], settings.uTorrent['port'], settings.uTorrent['ssl'])

    # Run a uTorrent action before conversion.
    session = None
    auth = None
    if web_ui:
        session = requests.Session()
        if session:
            auth, session = _authToken(session, host, settings.uTorrent['username'], settings.uTorrent['password'])
            if auth and settings.uTorrent['actionbefore']:
                params = {'token': auth, 'action': settings.uTorrent['actionbefore'], 'hash': torrent_hash}
                _sendRequest(session, host, settings.uTorrent['username'], settings.uTorrent['password'], params, None, "Before Function")
                log.debug("Sending action %s to uTorrent" % settings.uTorrent['actionbefore'])

    if settings.uTorrent['convert']:
        # Check for custom uTorrent output directory
        if settings.uTorrent['output-dir']:
            settings.output_dir = settings.uTorrent['output-dir']
            log.debug("Overriding output_dir to %s." % settings.uTorrent['output-dir'])

        # Perform conversion.
        log.info("Performing conversion")
        settings.delete = False
        if not settings.output_dir:
            suffix = "convert"
            if kind == 'single':
                log.info("Single File Torrent")
                settings.output_dir = os.path.join(path, ("%s-%s" % (re.sub(settings.regex, '_', name), suffix)))
            else:
                log.info("Multi File Torrent")
                settings.output_dir = os.path.abspath(os.path.join(path, '..', ("%s-%s" % (re.sub(settings.regex, '_', name), suffix))))
            if not os.path.exists(settings.output_dir):
                try:
                    os.makedirs(settings.output_dir)
                except:
                    log.exception("Error creating output directory.")
        else:
            settings.output_dir = re.sub(settings.regex, '_', os.path.abspath(os.path.join(settings.output_dir, re.sub(settings.regex, '_', name))))
            if not os.path.exists(settings.output_dir):
                try:
                    os.makedirs(settings.output_dir)
                except:
                    log.exception("Error creating output sub directory.")

        mp = MediaProcessor(settings)

        if kind == 'single':
            inputfile = os.path.join(path, filename)
            info = mp.isValidSource(inputfile)
            if info:
                log.info("Processing file %s." % inputfile)
                try:
                    output = mp.process(inputfile, info=info)
                    if not output:
                        log.error("No output file generated for single torrent download.")
                        sys.exit(1)
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
                    info = mp.isValidSource(inputfile)
                    if info and inputfile not in ignore:
                        log.info("Processing file %s." % inputfile)
                        try:
                            output = mp.process(inputfile, info=info)
                            if output and output.get('output'):
                                ignore.append(output.get('output'))
                            else:
                                log.error("Converting file failed %s." % inputfile)
                        except:
                            log.exception("Error converting file %s." % inputfile)
                    else:
                        log.debug("Ignoring file %s." % inputfile)
            if len(ignore) < 1:
                log.error("No output files generated for the entirety of this mutli file torrent, aborting.")
                sys.exit(1)

        path = settings.output_dir
        delete_dir = settings.output_dir
    else:
        suffix = "copy"
        # name = name[:260-len(suffix)]
        if kind == 'single':
            log.info("Single File Torrent")
            newpath = os.path.join(path, ("%s-%s" % (re.sub(settings.regex, '_', name), suffix)))
        else:
            log.info("Multi File Torrent")
            newpath = os.path.abspath(os.path.join(path, '..', ("%s-%s" % (re.sub(settings.regex, '_', name), suffix))))
        if not os.path.exists(newpath):
            try:
                os.makedirs(newpath)
                log.debug("Creating temporary directory %s" % newpath)
            except:
                log.exception("Error creating temporary directory.")
        if kind == 'single':
            inputfile = os.path.join(path, filename)
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

    if settings.uTorrent['sb'].startswith(label):
        log.info("Passing %s directory to Sickbeard." % path)
        autoProcessTV.processEpisode(path, settings, pathMapping=path_mapping)
    elif settings.uTorrent['sonarr'].startswith(label):
        log.info("Passing %s directory to Sonarr." % path)
        sonarr.processEpisode(path, settings, pathMapping=path_mapping)
    elif settings.uTorrent['radarr'].startswith(label):
        log.info("Passing %s directory to Radarr." % path)
        radarr.processMovie(path, settings, pathMapping=path_mapping)
    elif settings.uTorrent['sr'].startswith(label):
        log.info("Passing %s directory to Sickrage." % path)
        autoProcessTVSR.processEpisode(path, settings, pathMapping=path_mapping)
    elif [x for x in settings.uTorrent['bypass'] if x.startswith(label)]:
        log.info("Bypassing any further processing as per category.")

    # Run a uTorrent action after conversion.
    if web_ui:
        if session and auth and settings.uTorrent['actionafter']:
            params = {'token': auth, 'action': settings.uTorrent['actionafter'], 'hash': torrent_hash}
            _sendRequest(session, host, settings.uTorrent['username'], settings.uTorrent['password'], params, None, "After Function")
            log.debug("Sending action %s to uTorrent" % settings.uTorrent['actionafter'])

    if delete_dir:
        if os.path.exists(delete_dir):
            try:
                os.rmdir(delete_dir)
                log.debug("Successfully removed tempoary directory %s." % delete_dir)
            except:
                log.exception("Unable to delete temporary directory")
except:
    log.exception("Unexpected exception.")
    sys.exit(1)
