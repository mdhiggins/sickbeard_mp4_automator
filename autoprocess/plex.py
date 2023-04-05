#!/usr/bin/env python3
import logging
import os
import requests
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
from plexapi.library import LibrarySection
from resources.log import getLogger
from resources.readsettings import ReadSettings
from typing import List, Tuple


def refreshPlex(settings: ReadSettings, path: str = None, logger: logging.Logger = None):
    log = logger or getLogger(__name__)

    log.info("Starting Plex refresh.")

    targetpath = os.path.dirname(path)
    pathMapping = settings.Plex.get('path-mapping', {})

    # Path Mapping
    targetdirs = targetpath.split(os.sep)
    for k in sorted(pathMapping.keys(), reverse=True):
        mapdirs = k.split(os.sep)
        if mapdirs == targetdirs[:len(mapdirs)]:
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
                    log.info("Refreshing %s with path %s" % (section.title, targetpath))
    else:
        log.error("Unable to establish Plex server connection.")


def getPlexServer(settings: ReadSettings, logger: logging.Logger = None) -> Tuple[PlexServer, dict]:
    log = logger or getLogger(__name__)

    if not settings.Plex.get('username') and not settings.Plex.get('host'):
        log.error("No plex server settings specified, please update your configuration file.")
        return None, None

    plex: PlexServer = None
    session: requests.Session = None

    if settings.Plex.get('ignore_certs'):
        session = requests.Session()
        session.verify = False
        requests.packages.urllib3.disable_warnings()

    log.info("Connecting to Plex server...")
    if settings.Plex.get('username') and settings.Plex.get('servername'):
        try:
            account = None
            if settings.Plex.get('token'):
                try:
                    account = MyPlexAccount(username=settings.Plex.get('username'), token=settings.Plex.get('token'), session=session)
                except:
                    log.debug("Unable to connect using token, falling back to password.")
                    account = None
            if settings.Plex.get('username') and not account:
                try:
                    account = MyPlexAccount(username=settings.Plex.get('username'), password=settings.Plex.get('password'), session=session)
                except:
                    log.debug("Unable to connect using username/password.")
                    account = None
            if account:
                plex = account.resource(settings.Plex.get('servername')).connect()
            if plex:
                log.info("Connected to Plex server %s using plex.tv account." % (plex.friendlyName))
        except:
            log.exception("Error connecting to plex.tv account.")

    if not plex and settings.Plex.get('host') and settings.Plex.get('port') and settings.Plex.get('token'):
        protocol = "https://" if settings.Plex.get('ssl') else "http://"
        try:
            plex = PlexServer(protocol + settings.Plex.get('host') + ':' + str(settings.Plex.get('port')), settings.Plex.get('token'), session=session)
            log.info("Connected to Plex server %s using server settings." % (plex.friendlyName))
        except:
            log.exception("Error connecting to Plex server.")
    elif plex and settings.Plex.get('host') and settings.Plex.get('token'):
        log.debug("Connected to server using plex.tv account, ignoring manual server settings.")

    return plex
