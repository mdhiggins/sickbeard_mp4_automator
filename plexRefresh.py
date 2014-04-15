import urllib
from xml.dom import minidom

def PlexRefresh(settings):
    host = settings.Plex['host']
    port = settings.Plex['port']

    url = "http://%s:%s/library/sections" % (host, port)
    try:
        xml_sections = minidom.parse(urllib.urlopen(url))
    except IOError, e:
        print "Error: Count not contact Plex Media Server"
        print e
        return

    sections = xml_sections.getElementsByTagName('Directory')
    if not sections:
        print "Error: Plex Media Server is not running"
        return

    for s in sections:
        if s.getAttribute('type') == "show":
            url = "http://%s:%s/library/sections/%s/refresh" % (host, port, s.getAttribute('key'))
            try:
                urllib.urlopen(url)
            except Exception, e:
                print "Error opening Plex refresh URL"
                print e
                return