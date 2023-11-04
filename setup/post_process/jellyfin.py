#!/usr/bin/env python3
import requests

TOKEN = ""


def main():
    print("Jellyfin Post-Processing Refresh Script")
    url = "https://jellyfin.tld:8096/Library/Refresh"

    headers = {
        "X-MediaBrowser-Token": TOKEN
    }

    try:
        r = requests.post(url, headers=headers)
        print(r.status_code)
        print(r.text)
    except Exception as e:
        print("Error - Request failed")
        print(e)


if __name__ == "__main__":
    main()
