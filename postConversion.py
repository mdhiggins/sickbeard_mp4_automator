#!/usr/bin/env python
import os
import sys
import json
import urllib
import struct
import logging
from extensions import valid_tagging_extensions
from readSettings import ReadSettings
from autoprocess import plex
from tvdb_mp4 import Tvdb_mp4
from mkvtomp4 import MkvtoMp4
from post_processor import PostProcessor
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
log = logging.getLogger("SickbeardPostConversion")

log.info("Sickbeard extra script post processing started.")

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")

if len(sys.argv) > 4:
    inputfile = sys.argv[1]
    original = sys.argv[2]
    tvdb_id = int(sys.argv[3])
    season = int(sys.argv[4])
    episode = int(sys.argv[5])

    converter = MkvtoMp4(settings)

    log.debug("Input file: %s." % inputfile)
    log.debug("Original name: %s." % original)
    log.debug("TVDB ID: %s." % tvdb_id)
    log.debug("Season: %s episode: %s." % (season, episode))

    info = converter.isValidSource(inputfile)
    if info:
        log.info("Processing %s." % inputfile)

        output = converter.process(inputfile, original=original, info=info)

        if output:
            # Tag with metadata
            if settings.tagfile and output['output_extension'] in valid_tagging_extensions:
                log.info("Tagging %s with ID %s season %s episode %s." % (inputfile, tvdb_id, season, episode))
                try:
                    tagmp4 = Tvdb_mp4(tvdb_id, season, episode, original, language=settings.taglanguage)
                    tagmp4.setHD(output['x'], output['y'])
                    tagmp4.writeTags(output['output'], settings.artwork, settings.thumbnail)
                except:
                    log.error("Unable to tag file")

            # QTFS
            if settings.relocate_moov and output['output_extension'] in valid_tagging_extensions:
                converter.QTFS(output['output'])

            # Copy to additional locations
            output_files = converter.replicate(output['output'])

            # run any post process scripts
            if settings.postprocess:
                post_processor = PostProcessor(output_files, log)
                post_processor.setTV(tvdb_id, season, episode)
                post_processor.run_scripts()

            try:
                refresh = json.load(urllib.urlopen(settings.getRefreshURL(tvdb_id)))
                for item in refresh:
                    log.debug(refresh[item])
            except (IOError, ValueError):
                log.exception("Couldn't refresh Sickbeard, check your autoProcess.ini settings.")

            plex.refreshPlex(settings, 'show', log)

else:
    log.error("Not enough command line arguments present %s." % len(sys.argv))
    sys.exit()
