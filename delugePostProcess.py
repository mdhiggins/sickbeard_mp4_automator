#!/usr/bin/env python3

import os
import sys
from autoprocess import autoProcessTV, autoProcessMovie, autoProcessTVSR, sonarr, radarr
from resources.readsettings import ReadSettings
from resources.mediaprocessor import MediaProcessor
from resources.log import getLogger
from deluge_client import DelugeRPCClient
import shutil

log = getLogger("DelugePostProcess")

log.info("Deluge post processing started.")

try:
    settings = ReadSettings()
    categories = [settings.deluge['sb'], settings.deluge['cp'], settings.deluge['sonarr'], settings.deluge['radarr'], settings.deluge['sr'], settings.deluge['bypass']]
    remove = settings.deluge['remove']

    if len(sys.argv) < 4:
        log.error("Not enough command line parameters present, are you launching this from deluge?")
        sys.exit(1)

    path = str(sys.argv[3])
    torrent_name = str(sys.argv[2])
    torrent_id = str(sys.argv[1])
    delete_dir = None

    log.debug("Path: %s." % path)
    log.debug("Torrent: %s." % torrent_name)
    log.debug("Hash: %s." % torrent_id)

    client = DelugeRPCClient(host=settings.deluge['host'], port=int(settings.deluge['port']), username=settings.deluge['user'], password=settings.deluge['pass'])
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

    if len([x for x in categories if x.startswith(category)]) < 1:
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
                settings.output_dir = os.path.join(path, ("%s-%s" % (torrent_name, suffix)))
            else:
                settings.output_dir = os.path.join(settings.output_dir, torrent_name)
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
            newpath = os.path.join(path, ("%s-%s" % (torrent_name, suffix)))
            if not os.path.exists(newpath):
                try:
                    os.mkdir(newpath)
                except:
                    log.exception("Unable to make copy directory %s." % newpath)
            for inputfile in files:
                log.info("Copying file %s to %s." % (inputfile, newpath))
                shutil.copy(inputfile, newpath)
            path = newpath
            delete_dir = newpath
    except:
        log.exception("Error occurred handling file")

    if categories[0].startswith(category):
        log.info("Passing %s directory to Sickbeard." % path)
        autoProcessTV.processEpisode(path, settings)
    elif categories[1].startswith(category):
        log.info("Passing %s directory to Couch Potato." % path)
        autoProcessMovie.process(path, settings, torrent_name)
    elif categories[2].startswith(category):
        log.info("Passing %s directory to Sonarr." % path)
        sonarr.processEpisode(path, settings)
    elif categories[3].startswith(category):
        log.info("Passing %s directory to Radarr." % path)
        radarr.processMovie(path, settings)
    elif categories[4].startswith(category):
        log.info("Passing %s directory to Sickrage." % path)
        autoProcessTVSR.processEpisode(path, settings)
    elif categories[5].startswith(category):
        log.info("Bypassing any further processing as per category.")

    if delete_dir:
        if os.path.exists(delete_dir):
            try:
                os.rmdir(delete_dir)
                log.debug("Successfully removed tempoary directory %s." % delete_dir)
            except:
                log.exception("Unable to delete temporary directory.")

    if remove:
        try:
            client.call('core.remove_torrent', torrent_id, True)
        except:
            log.exception("Unable to remove torrent from deluge.")
except:
    log.exception("Unexpected exception.")
    sys.exit(1)
