#!/usr/bin/env python3

import os
import re
import sys
import shutil
from autoprocess import autoProcessTV, autoProcessTVSR, sonarr, radarr, whisparr
from resources.log import getLogger
from resources.readsettings import ReadSettings
from resources.mediaprocessor import MediaProcessor

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
    categories = [settings.qBittorrent['sb'], settings.qBittorrent['sonarr'], settings.qBittorrent['radarr'], settings.qBittorrent['whisparr'], settings.qBittorrent['sr']] + settings.qBittorrent['bypass']
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

    try:
        import qbittorrentapi
    except ImportError:
        log.exception("Python module qbittorrent-api is required. Install with 'pip install qbittorrent-api' then try again.")
        sys.exit(1)

    delete_dir = False

    protocol = "https" if settings.qBittorrent['ssl'] else "http"
    host = "%s://%s:%s" % (protocol, settings.qBittorrent['host'], settings.qBittorrent['port'])

    qb = qbittorrentapi.Client(
        host=host,
        username=settings.qBittorrent['username'],
        password=settings.qBittorrent['password'],
        VERIFY_WEBUI_CERTIFICATE=False if settings.qBittorrent['ssl'] else True
    )

    if settings.qBittorrent['actionbefore']:
        if settings.qBittorrent['actionbefore'] in ['pause', 'stop']:
            log.debug("Sending action stop to qBittorrent")
            qb.torrents_stop(torrent_hashes=torrent_hash)

    if settings.qBittorrent['convert']:
        if settings.qBittorrent['output-dir']:
            settings.output_dir = settings.qBittorrent['output-dir']
            log.debug("Overriding output_dir to %s." % settings.qBittorrent['output-dir'])

        log.info("Performing conversion")
        settings.delete = False
        if not settings.output_dir:
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
    elif settings.qBittorrent['whisparr'].startswith(label):
        log.info("Passing %s directory to Whisparr." % path)
        whisparr.processMovie(path, settings, pathMapping=path_mapping)
    elif settings.qBittorrent['sr'].startswith(label):
        log.info("Passing %s directory to Sickrage." % path)
        autoProcessTVSR.processEpisode(path, settings, pathMapping=path_mapping)
    elif [x for x in settings.qBittorrent['bypass'] if x.startswith(label)]:
        log.info("Bypassing any further processing as per category.")

    if settings.qBittorrent['actionafter']:
        if settings.qBittorrent['actionafter'] in ['resume', 'start']:
            log.debug("Sending action start to qBittorrent")
            qb.torrents_start(torrent_hashes=torrent_hash)
        elif settings.qBittorrent['actionafter'] == 'delete':
            log.debug("Sending action delete to qBittorrent")
            qb.torrents_delete(torrent_hashes=torrent_hash, delete_files=False)
        elif settings.qBittorrent['actionafter'] == 'deletedata':
            log.debug("Sending action deletedata to qBittorrent")
            qb.torrents_delete(torrent_hashes=torrent_hash, delete_files=True)

    if delete_dir:
        if os.path.exists(delete_dir):
            if not os.listdir(delete_dir):
                try:
                    os.rmdir(delete_dir)
                    log.debug("Successfully removed temporary directory %s." % delete_dir)
                except OSError:
                    log.warning("Unable to delete temporary directory %s (still in use or not empty)" % delete_dir)
            else:
                log.debug("Temporary directory %s is not empty, will not delete." % delete_dir)
except:
    log.exception("Unexpected exception.")
    sys.exit(1)
    