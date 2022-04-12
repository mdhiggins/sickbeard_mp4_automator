#!/usr/bin/env python3
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
import os

USERNAME = ""
TOKEN = ""
SERVERNAME = ""


def main():
    print("Plex Post-Processing Refresh Script")
    account = MyPlexAccount(username=USERNAME, token=TOKEN)
    plex: PlexServer = account.resource(SERVERNAME).connect()
    sectionType = "show" if os.env.get("SMA_SEASON") or os.env.get("SMA_EPISODE") else "movie"
    for section in plex.library.sections():
        if section.type == sectionType:
            print("Updating section %s on server %s" % (section.title, SERVERNAME))
            section.update()


if __name__ == "__main__":
    main()
