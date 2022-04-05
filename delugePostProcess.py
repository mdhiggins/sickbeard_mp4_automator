#!/usr/bin/env python3

import os
import sys
import re
from autoprocess import autoProcessTV, autoProcessTVSR, sonarr, radarr
from resources.readsettings import ReadSettings
from resources.mediaprocessor import MediaProcessor
from resources.log import getLogger
from deluge_client import DelugeRPCClient
import shutil

import ssl
import socket
import warnings

PY310_OR_LATER = sys.version_info[0] >= 3 and sys.version_info[1] >= 10

warnings.filterwarnings("ignore", category=DeprecationWarning)


# Fix for python 3.10 SSL issues
class SMADelugeRPCClient(DelugeRPCClient):
    def _create_socket(self, ssl_version=None):
        if ssl_version is not None:
            self._socket = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM), ssl_version=ssl_version, ciphers="AES256-SHA")
        else:
            self._socket = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM), ciphers="AES256-SHA")
        self._socket.settimeout(self.timeout)


log = getLogger("DelugePostProcess")

log.info("Deluge post processing started.")

DRPCClient = SMADelugeRPCClient if PY310_OR_LATER else DelugeRPCClient

try:
    settings = ReadSettings()
    categories = [settings.deluge['sb'], settings.deluge['sonarr'], settings.deluge['radarr'], settings.deluge['sr'], settings.deluge['bypass']]
    remove = settings.deluge['remove']

    if len(sys.argv) < 4:
        log.error("Not enough command line parameters present, are you launching this from deluge?")
        sys.exit(1)

    path = str(sys.argv[3])
    torrent_name = str(sys.argv[2])
    torrent_id = str(sys.argv[1])
    delete_dir = None
    path_mapping = settings.deluge['path-mapping']

    log.debug("Path: %s." % path)
    log.debug("Torrent: %s." % torrent_name)
    log.debug("Hash: %s." % torrent_id)

    client = DRPCClient(host=settings.deluge['host'], port=int(settings.deluge['port']), username=settings.deluge['user'], password=settings.deluge['pass'])
    client.connect()

    if client.connected:
        log.info("Successfully connected to Deluge")
    else:
        log.error("Failed to connect to Deluge")
        sys.exit(1)

    torrent_data = client.call('core.get_torrent_status', torrent_id, ['files', 'label'])
    try:
        torrent_files = torrent_data[b'files']
        category = torrent_data[b'label'].lower().decode()
    except:
        torrent_files = torrent_data['files']
        category = torrent_data['label'].lower()

    files = []

    # Check forcepath which overrides talking to deluge for files and instead reads the path
    try:
        force = (str(sys.argv[4]).lower().strip() == 'forcepath')
    except:
        force = False

    if force:
        log.debug("List of files in path override:")
        if os.path.isdir(path):
            for r, d, f in os.walk(path):
                for file in f:
                    files.append(os.path.join(r, file))
                    log.debug(os.path.join(r, file))
        else:
            log.debug(path)
            files.append(path)
            path = os.path.dirname(path)
    else:
        log.debug("List of files in torrent:")
        for contents in torrent_files:
            try:
                files.append(os.path.join(path, contents[b'path'].decode()))
                log.debug(os.path.join(path, contents[b'path'].decode()))
            except:
                files.append(os.path.join(path, contents['path']))
                log.debug(os.path.join(path, contents['path']))

    if not category or len([x for x in categories if x.startswith(category)]) < 1:
        log.error("No valid category detected.")
        sys.exit(1)

    if len(categories) != len(set(categories)):
        log.error("Duplicate category detected. Category names must be unique.")
        sys.exit(1)

    try:
        if settings.deluge['convert']:
            # Check for custom Deluge output_dir
            if settings.deluge['output_dir']:
                settings.output_dir = settings.deluge['output_dir']
                log.debug("Overriding output_dir to %s." % settings.deluge['output_dir'])

            # Perform conversion.
            settings.delete = False
            if not settings.output_dir:
                suffix = "convert"
                settings.output_dir = os.path.join(path, ("%s-%s" % (re.sub(settings.regex, '_', torrent_name), suffix)))
            else:
                settings.output_dir = os.path.join(settings.output_dir, re.sub(settings.regex, '_', torrent_name))
            if not os.path.exists(settings.output_dir):
                try:
                    os.makedirs(settings.output_dir)
                    delete_dir = settings.output_dir
                except:
                    log.exception("Unable to make output directory %s." % settings.output_dir)

            mp = MediaProcessor(settings)

            if len(files) < 1:
                log.error("No files provided by torrent")

            ignore = []
            for inputfile in files:
                info = mp.isValidSource(inputfile)
                if info and inputfile not in ignore:
                    log.info("Processing file %s." % inputfile)
                    try:
                        output = mp.process(inputfile, info=info)
                        if output and output.get('output'):
                            log.info("Successfully processed %s." % inputfile)
                            ignore.append(output.get('output'))
                        else:
                            log.error("Converting file failed %s." % inputfile)
                    except:
                        log.exception("Error converting file %s." % inputfile)
            if len(ignore) < 1:
                log.error("No valid files detected for conversion in download, aborting.")
                sys.exit(1)

            path = settings.output_dir
        else:
            suffix = "copy"
            newpath = os.path.join(path, ("%s-%s" % (re.sub(settings.regex, '_', torrent_name), suffix)))
            if not os.path.exists(newpath):
                try:
                    os.makedirs(newpath)
                except:
                    log.exception("Unable to make copy directory %s." % newpath)
            for inputfile in files:
                log.info("Copying file %s to %s." % (inputfile, newpath))
                shutil.copy(inputfile, newpath)
            path = newpath
            delete_dir = newpath
    except:
        log.exception("Error occurred handling file")

    if settings.deluge['sb'].startswith(category):
        log.info("Passing %s directory to Sickbeard." % path)
        autoProcessTV.processEpisode(path, settings, pathMapping=path_mapping)
    elif settings.deluge['sonarr'].startswith(category):
        log.info("Passing %s directory to Sonarr." % path)
        sonarr.processEpisode(path, settings, pathMapping=path_mapping)
    elif settings.deluge['radarr'].startswith(category):
        log.info("Passing %s directory to Radarr." % path)
        radarr.processMovie(path, settings, pathMapping=path_mapping)
    elif settings.deluge['sr'].startswith(category):
        log.info("Passing %s directory to Sickrage." % path)
        autoProcessTVSR.processEpisode(path, settings, pathMapping=path_mapping)
    elif settings.deluge['bypass'].startswith(category):
        log.info("Bypassing any further processing as per category.")

    if remove:
        try:
            client.call('core.remove_torrent', torrent_id, True)
        except:
            log.exception("Unable to remove torrent from deluge.")

    if delete_dir:
        if os.path.exists(delete_dir):
            if os.listdir(delete_dir):
                try:
                    os.rmdir(delete_dir)
                    log.debug("Successfully removed tempoary directory %s." % delete_dir)
                except:
                    log.exception("Unable to delete temporary directory.")
            else:
                log.debug("Temporary directory %s is not empty, will not delete." % delete_dir)
except:
    log.exception("Unexpected exception.")
    sys.exit(1)
