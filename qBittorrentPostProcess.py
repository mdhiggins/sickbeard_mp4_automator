import os
import re
import sys
import shutil
from autoprocess import autoProcessTV, autoProcessMovie, autoProcessTVSR, sonarr, radarr
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4
import logging
from logging.config import fileConfig

logpath = '/var/log/sickbeard_mp4_automator'
if os.name == 'nt':
    logpath = os.path.dirname(sys.argv[0])
elif not os.path.isdir(logpath):
    try:
        os.mkdir(logpath)
    except:
        logpath = os.path.dirname(sys.argv[0])
configPath = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), 'logging.ini')).replace("\\", "\\\\")
logPath = os.path.abspath(os.path.join(logpath, 'index.log')).replace("\\", "\\\\")
fileConfig(configPath, defaults={'logfilename': logPath})
log = logging.getLogger("qBittorrentPostProcess")

log.info("qBittorrent post processing started.")

if len(sys.argv) != 7:
    log.error("Not enough command line parameters present, are you launching this from qBittorrent?")
    log.error("#Args: %L %T %R %F %N %I Category, Tracker, RootPath, ContentPath , TorrentName, InfoHash")
    log.error("Length was %s" % str(len(sys.argv)))
    log.error(str(sys.argv[1:]))
    sys.exit()

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
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

qb = Client(settings.qBittorrentHost)

if settings.qBittorrentActionBefore:
  qb.login(settings.qBittorrentUsername, settings.qBittorrentPassword)
  if settings.qBittorrentActionBefore == 'pause': #currently only support pausing
    log.debug("Sending action %s to qBittorrent" % settings.qBittorrentActionBefore)
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
      #If the user hasn't set an output directory, go up one from the root path and create a directory there as [name]-convert
      suffix = "convert"
      settings.output_dir = os.path.abspath(os.path.join(root_path, '..', ("%s-%s" % (name, suffix))))
      if not os.path.exists(settings.output_dir):
          os.mkdir(settings.output_dir)
      delete_dir = settings.output_dir

    converter = MkvtoMp4(settings)

    if single_file:
        #single file
        inputfile = content_path
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
        for r, d, f in os.walk(root_path):
            for files in f:
                inputfile = os.path.join(r, files)
                if MkvtoMp4(settings).validSource(inputfile) and inputfile not in ignore:
                    log.info("Processing file %s." % inputfile)
                    try:
                        output = converter.process(inputfile)
                        if output is not False:
                            ignore.append(output['output'])
                        else:
                            log.error("Converting file failed %s." % inputfile)
                    except:
                        log.exception("Error converting file %s." % inputfile)
                else:
                    log.debug("Ignoring file %s." % inputfile)

    path = converter.output_dir
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
if settings.qBittorrentActionAfter:
    qb.login(settings.qBittorrentUsername, settings.qBittorrentPassword)
    #currently only support resuming or deleting torrent
    if settings.qBittorrentActionAfter == 'resume': 
        log.debug("Sending action %s to qBittorrent" % settings.qBittorrentActionBefore)
        qb.resume(torrent_hash)
    elif settings.qBittorrentActionAfter == 'delete':
        #this will delete the torrent from qBittorrent but it WILL NOT delete the data
        log.debug("Sending action %s to qBittorrent" % settings.qBittorrentActionBefore)
        qb.delete(torrent_hash)

if delete_dir:
    if os.path.exists(delete_dir):
        try:
            os.rmdir(delete_dir)
            log.debug("Successfully removed tempoary directory %s." % delete_dir)
        except:
            log.exception("Unable to delete temporary directory")

sys.exit()
