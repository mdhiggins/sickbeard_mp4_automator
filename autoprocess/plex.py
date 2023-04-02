#!/usr/bin/env python3
import logging
import os
import requests
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
from plexapi.library import LibrarySection
from resources.log import getLogger
from resources.readsettings import ReadSettings
from typing import List, Tuple, Dict


def refreshPlex(settings: ReadSettings, path: str = None, logger: logging.Logger = None):
    log = logger or getLogger(__name__)

    log.info("Starting Plex refresh.")

    targetpath = os.path.dirname(path)
    pathMapping = settings.plex.get('path-mapping', {})

    # Path Mapping
    for k in pathMapping:
        if os.path.commonprefix([targetpath, k]) == k:
            targetpath = os.path.join(pathMapping[k], os.path.relpath(targetpath, k))
            log.debug("PathMapping match found, replacing %s with %s, final directory is %s." % (k, pathMapping[k], targetpath))
            break

    plex = getPlexServer(settings, log)

    log.info("Checking if any sections contain the path %s." % (targetpath))

    if plex:
        sections: List[LibrarySection] = plex.library.sections()

        section: LibrarySection
        for section in sections:
            location: str
            for location in section.locations:
                log.debug("Checking section %s path %s." % (section.title, location))
                if os.path.commonprefix([targetpath, location]) == location:
                    section.update(path=targetpath)
                    log.info("Refreshing %s with path %s" % (section.title, path))
    else:
        log.error("Unable to establish Plex server connection.")


def getPlexServer(settings: ReadSettings, logger: logging.Logger = None) -> Tuple[PlexServer, dict]:
    log = logger or getLogger(__name__)

    if not settings.plex.get('username') and not settings.plex.get('host'):
        log.error("No plex server settings specified, please update your configuration file.")
        return None, None

    plex: PlexServer = None
    session: requests.Session = None

    if settings.plex.get('ignore_certs'):
        session = requests.Session()
        session.verify = False
        requests.packages.urllib3.disable_warnings()

    log.info("Connecting to Plex server...")
    if settings.plex.get('username') and settings.plex.get('servername'):
        try:
            account = None
            if settings.plex.get('token'):
                try:
                    account = MyPlexAccount(username=settings.plex.get('username'), token=settings.plex.get('token'), session=session)
                except:
                    log.debug("Unable to connect using token, falling back to password.")
                    account = None
            if settings.plex.get('username') and not account:
                try:
                    account = MyPlexAccount(username=settings.plex.get('username'), password=settings.plex.get('password'), session=session)
                except:
                    log.debug("Unable to connect using username/password.")
                    account = None
            if account:
                plex = account.resource(settings.plex.get('servername')).connect()
            if plex:
                log.info("Connected to Plex server %s using plex.tv account." % (plex.friendlyName))
        except:
            log.exception("Error connecting to plex.tv account.")

    if not plex and settings.plex.get('host') and settings.plex.get('port') and settings.plex.get('token'):
        protocol = "https://" if settings.plex.get('ssl') else "http://"
        try:
            plex = PlexServer(protocol + settings.plex.get('host') + ':' + str(settings.plex.get('port')), settings.plex.get('token'), session=session)
            log.info("Connected to Plex server %s using server settings." % (plex.friendlyName))
        except:
            log.exception("Error connecting to Plex server.")
    elif plex and settings.plex.get('host') and settings.plex.get('token'):
        log.debug("Connected to server using plex.tv account, ignoring manual server settings.")

    return plex
