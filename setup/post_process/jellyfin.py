#!/usr/bin/env python3
import requests

TOKEN = ""


def main():
    print("Jellyfin Post-Processing Refresh Script")
    url = "https://jellyfin.tld/library/refresh"

    headers = {
        "X-MediaBrowser-Token": TOKEN
    }

    try:
        r = requests.get(url, headers=headers)
        print(r.status_code)
        print(r.json())
    except Exception as e:
        print("Error - Request failed")
        print(e)


if __name__ == "__main__":
    main()
