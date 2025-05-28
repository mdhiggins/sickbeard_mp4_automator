#!/usr/bin/env python3

import os
import re
import sys
import shutil
from autoprocess import autoProcessTV, autoProcessTVSR, sonarr, radarr
from resources.log import getLogger
from resources.readsettings import ReadSettings
from resources.mediaprocessor import MediaProcessor


def getHost(host='localhost', port=8080, ssl=False):
    protocol = "https://" if ssl else "http://"
    return protocol + host + ":" + str(port) + "/"


log = getLogger("qBittorrentPostProcess")

log.info("qBittorrent post processing started.")

if len(sys.argv) < 6:
    log.error("Not enough command line parameters present, are you launching this from qBittorrent?")
    log.error("#Args: %L %T %R %F %N %I Category, Tracker, RootPath, ContentPath , TorrentName, InfoHash")
    log.error("Length was %s" % str(len(sys.argv)))
    log.error(str(sys.argv[1:]))
    sys.exit(1)

try:
    settings = ReadSettings()
    label = sys.argv[1].lower().strip()
    if len(sys.argv) == 6:
        root_path = str(sys.argv[3])
        content_path = str(sys.argv[3])
        name = sys.argv[4]
        torrent_hash = sys.argv[5]
    else:
        root_path = str(sys.argv[3])
        content_path = str(sys.argv[4])
        name = sys.argv[5]
        torrent_hash = sys.argv[6]

    if not root_path:
        root_path = os.path.dirname(content_path)
    categories = [settings.qBittorrent['sb'], settings.qBittorrent['sonarr'], settings.qBittorrent['radarr'], settings.qBittorrent['sr']] + settings.qBittorrent['bypass']
    path_mapping = settings.qBittorrent['path-mapping']

    log.debug("Root Path: %s." % root_path)
    log.debug("Content Path: %s." % content_path)
    log.debug("Label: %s." % label)
    log.debug("Categories: %s." % categories)
    log.debug("Torrent hash: %s." % torrent_hash)
    log.debug("Torrent name: %s." % name)

    single_file = os.path.isfile(content_path)

    if not label or len([x for x in categories if x.startswith(label)]) < 1:
        log.error("No valid label detected.")
        sys.exit(1)

    if len(categories) != len(set(categories)):
        log.error("Duplicate category detected. Category names must be unique.")
        sys.exit(1)

    # Import python-qbittorrent
    try:
        from qbittorrent import Client
    except ImportError:
        log.exception("Python module PYTHON-QBITTORRENT is required. Install with 'pip install python-qbittorrent' then try again.")
        sys.exit(1)

    delete_dir = False

    host = getHost(settings.qBittorrent['host'], settings.qBittorrent['port'], settings.qBittorrent['ssl'])

    qb = Client(host)
    qb.login(settings.qBittorrent['username'], settings.qBittorrent['password'])

    if settings.qBittorrent['actionbefore']:
        if settings.qBittorrent['actionbefore'] == 'pause':  # currently only support pausing
            log.debug("Sending action %s to qBittorrent" % settings.qBittorrent['actionbefore'])
            qb.pause(torrent_hash)

    if settings.qBittorrent['convert']:
        # Check for custom qBittorrent output directory
        if settings.qBittorrent['output-dir']:
            settings.output_dir = settings.qBittorrent['output-dir']
            log.debug("Overriding output_dir to %s." % settings.qBittorrent['output-dir'])

        # Perform conversion.
        log.info("Performing conversion")
        settings.delete = False
        if not settings.output_dir:
            # If the user hasn't set an output directory, go up one from the root path and create a directory there as [name]-convert
            suffix = "convert"
            settings.output_dir = os.path.abspath(os.path.join(root_path, '..', ("%s-%s" % (re.sub(settings.regex, '_', name), suffix))))
        else:
            settings.output_dir = os.path.join(settings.output_dir, re.sub(settings.regex, '_', name))
        if not os.path.exists(settings.output_dir):
            try:
                os.makedirs(settings.output_dir)
                delete_dir = settings.output_dir
            except:
                log.exception("Unable to make output directory %s." % settings.output_dir)

        mp = MediaProcessor(settings)

        if single_file:
            # single file
            inputfile = content_path
            info = mp.isValidSource(inputfile)
            if info:
                log.info("Processing file %s." % inputfile)
                try:
                    output = mp.process(inputfile, reportProgress=True, info=info)
                    if not output:
                        log.error("No output file generated for single torrent download.")
                        sys.exit(1)
                except:
                    log.exception("Error converting file %s." % inputfile)
        else:
            log.debug("Processing multiple files.")
            ignore = []
            for r, d, f in os.walk(root_path):
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
    else:
        suffix = "copy"
        # name = name[:260-len(suffix)]
        if single_file:
            log.info("Single File Torrent")
            root, filename = os.path.split(root_path)
            filename, extension = os.path.splitext(filename)
            newpath = os.path.join(root, ("%s-%s" % (re.sub(settings.regex, '_', filename), suffix)))
        else:
            log.info("Multi File Torrent")
            newpath = os.path.abspath(os.path.join(root_path, '..', ("%s-%s" % (re.sub(settings.regex, '_', name), suffix))))

        if not os.path.exists(newpath):
            os.makedirs(newpath)
            log.debug("Creating temporary directory %s" % newpath)

        if single_file:
            inputfile = content_path
            shutil.copy(inputfile, newpath)
            log.debug("Copying %s to %s" % (inputfile, newpath))
        else:
            for r, d, f in os.walk(root_path):
                for files in f:
                    inputfile = os.path.join(r, files)
                    shutil.copy(inputfile, newpath)
                    log.debug("Copying %s to %s" % (inputfile, newpath))
        path = newpath
        delete_dir = newpath

    if settings.qBittorrent['sb'].startswith(label):
        log.info("Passing %s directory to Sickbeard." % path)
        autoProcessTV.processEpisode(path, settings, pathMapping=path_mapping)
    elif settings.qBittorrent['sonarr'].startswith(label):
        log.info("Passing %s directory to Sonarr." % path)
        sonarr.processEpisode(path, settings, pathMapping=path_mapping)
    elif settings.qBittorrent['radarr'].startswith(label):
        log.info("Passing %s directory to Radarr." % path)
        radarr.processMovie(path, settings, pathMapping=path_mapping)
    elif settings.qBittorrent['sr'].startswith(label):
        log.info("Passing %s directory to Sickrage." % path)
        autoProcessTVSR.processEpisode(path, settings, pathMapping=path_mapping)
    elif [x for x in settings.qBittorrent['bypass'] if x.startswith(label)]:
        log.info("Bypassing any further processing as per category.")

    # Run a qbittorrent action after conversion.
    if settings.qBittorrent['actionafter']:
        # currently only support resuming or deleting torrent
        if settings.qBittorrent['actionafter'] == 'resume':
            log.debug("Sending action %s to qBittorrent" % settings.qBittorrent['actionafter'])
            qb.resume(torrent_hash)
        elif settings.qBittorrent['actionafter'] == 'delete':
            # this will delete the torrent from qBittorrent but it WILL NOT delete the data
            log.debug("Sending action %s to qBittorrent" % settings.qBittorrent['actionafter'])
            qb.delete(torrent_hash)
        elif settings.qBittorrent['actionafter'] == 'deletedata':
            # this will delete the torrent from qBittorrent and delete data
            log.debug("Sending action %s to qBittorrent" % settings.qBittorrent['actionafter'])
            qb.delete_permanently(torrent_hash)

    if delete_dir:
        if os.path.exists(delete_dir):
            if os.listdir(delete_dir):
                try:
                    os.rmdir(delete_dir)
                    log.debug("Successfully removed tempoary directory %s." % delete_dir)
                except:
                    log.exception("Unable to delete temporary directory")
            else:
                log.debug("Temporary directory %s is not empty, will not delete." % delete_dir)
except:
    log.exception("Unexpected exception.")
    sys.exit(1)
