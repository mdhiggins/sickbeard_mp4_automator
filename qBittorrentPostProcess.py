#!/usr/bin/env python

import os
import re
import sys
import shutil
from log import getLogger
from autoprocess import autoProcessTV, autoProcessMovie, autoProcessTVSR, sonarr, radarr
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4
import logging
from logging.config import fileConfig

log = getLogger("qBittorrentPostProcess")

log.info("qBittorrent post processing started.")

if len(sys.argv) != 7:
    log.error("Not enough command line parameters present, are you launching this from qBittorrent?")
    log.error("#Args: %L %T %R %F %N %I Category, Tracker, RootPath, ContentPath , TorrentName, InfoHash")
    log.error("Length was %s" % str(len(sys.argv)))
    log.error(str(sys.argv[1:]))
    sys.exit()

settings = ReadSettings()
label = sys.argv[1].lower()
root_path = str(sys.argv[3])
content_path = str(sys.argv[4])
name = sys.argv[5]
torrent_hash = sys.argv[6]
categories = [settings.qBittorrent['cp'], settings.qBittorrent['sb'], settings.qBittorrent['sonarr'], settings.qBittorrent['radarr'], settings.qBittorrent['sr'], settings.qBittorrent['bypass']]

log.debug("Root Path: %s." % root_path)
log.debug("Label: %s." % label)
log.debug("Categories: %s." % categories)
log.debug("Torrent hash: %s." % torrent_hash)
log.debug("Torrent name: %s." % name)

if root_path == content_path:
    single_file = False
else:
    single_file = True

if label not in categories:
    log.error("No valid label detected.")
    sys.exit()

if len(categories) != len(set(categories)):
    log.error("Duplicate category detected. Category names must be unique.")
    sys.exit()

# Import python-qbittorrent
try:
    from qbittorrent import Client
except ImportError:
    log.exception("Python module PYTHON-QBITTORRENT is required. Install with 'pip install python-qbittorrent' then try again.")
    sys.exit()

delete_dir = False

qb = Client(settings.qBittorrent['host'])
qb.login(settings.qBittorrent['username'], settings.qBittorrent['password'])

if settings.qBittorrent['actionBefore']:
    if settings.qBittorrent['actionBefore'] == 'pause':  # currently only support pausing
        log.debug("Sending action %s to qBittorrent" % settings.qBittorrent['actionBefore'])
        qb.pause(torrent_hash)

if settings.qBittorrent['convert']:
    # Check for custom qBittorrent output_dir
    if settings.qBittorrent['output_dir']:
        settings.output_dir = settings.qBittorrent['output_dir']
        log.debug("Overriding output_dir to %s." % settings.qBittorrent['output_dir'])

    # Perform conversion.
    log.info("Performing conversion")
    settings.delete = False
    if not settings.output_dir:
        # If the user hasn't set an output directory, go up one from the root path and create a directory there as [name]-convert
        suffix = "convert"
        settings.output_dir = os.path.abspath(os.path.join(root_path, '..', ("%s-%s" % (name, suffix))))
    else:
        settings.output_dir = os.path.join(settings.output_dir, name)
    if not os.path.exists(settings.output_dir):
        try:
            os.makedirs(settings.output_dir)
            delete_dir = settings.output_dir
        except:
            log.exception("Unable to make output directory %s." % settings.output_dir)

    converter = MkvtoMp4(settings)

    if single_file:
        # single file
        inputfile = content_path
        info = converter.isValidSource(inputfile)
        if info:
            log.info("Processing file %s." % inputfile)
            try:
                output = converter.process(inputfile, reportProgress=True, info=info)
            except:
                log.exception("Error converting file %s." % inputfile)
        else:
            log.debug("Ignoring file %s." % inputfile)
    else:
        log.debug("Processing multiple files.")
        ignore = []
        for r, d, f in os.walk(root_path):
            for files in f:
                inputfile = os.path.join(r, files)
                info = converter.isValidSource(inputfile)
                if info and inputfile not in ignore:
                    log.info("Processing file %s." % inputfile)
                    try:
                        output = converter.process(inputfile, info=info)
                        if output is not False:
                            ignore.append(output['output'])
                        else:
                            log.error("Converting file failed %s." % inputfile)
                    except:
                        log.exception("Error converting file %s." % inputfile)
                else:
                    log.debug("Ignoring file %s." % inputfile)

    path = settings.output_dir
else:
    suffix = "copy"
    # name = name[:260-len(suffix)]
    if single_file:
        log.info("Single File Torrent")
        newpath = os.path.join(path, ("%s-%s" % (name, suffix)))
    else:
        log.info("Multi File Torrent")
        newpath = os.path.abspath(os.path.join(root_path, '..', ("%s-%s" % (name, suffix))))

    if not os.path.exists(newpath):
        os.mkdir(newpath)
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

# Run a qbittorrent action after conversion.
if settings.qBittorrent['actionAfter']:
    # currently only support resuming or deleting torrent
    if settings.qBittorrent['actionAfter'] == 'resume':
        log.debug("Sending action %s to qBittorrent" % settings.qBittorrent['actionAfter'])
        qb.resume(torrent_hash)
    elif settings.qBittorrent['actionAfter'] == 'delete':
        # this will delete the torrent from qBittorrent but it WILL NOT delete the data
        log.debug("Sending action %s to qBittorrent" % settings.qBittorrent['actionAfter'])
        qb.delete(torrent_hash)
    elif settings.qBittorrent['actionAfter'] == 'deletedata':
        # this will delete the torrent from qBittorrent and delete data
        log.debug("Sending action %s to qBittorrent" % settings.qBittorrent['actionAfter'])
        qb.delete_permanently(torrent_hash)

if delete_dir:
    if os.path.exists(delete_dir):
        try:
            os.rmdir(delete_dir)
            log.debug("Successfully removed tempoary directory %s." % delete_dir)
        except:
            log.exception("Unable to delete temporary directory")

sys.exit()
