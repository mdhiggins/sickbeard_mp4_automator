#!/usr/bin/env python3
import requests

BASEURL = "http://localhost:8096"
APIKEY = ""


def main():
    print("Emby Post-Processing Refresh Script")
    url = "%s/emby/Library/Refresh?api_key=%s" % (BASEURL, APIKEY)

    try:
        r = requests.post(url)
        print(r.status_code)
        print(r.json())
    except Exception as e:
        print("Error - Request failed")
        print(e)


if __name__ == "__main__":
    main()
