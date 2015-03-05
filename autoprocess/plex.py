#!/usr/bin/env python
import urllib
from xml.dom import minidom

def refreshPlex(settings, source_type):
	host = settings.Plex['host']
	port = settings.Plex['port']
	approved_sources = ['movie', 'show']
	if settings.Plex['refresh'] and source_type in approved_sources:
		base_url = 'http://%s:%s/library/sections' % (host, port)
		refresh_url = '%s/%%s/refresh' % base_url

		try:
		  xml_sections = minidom.parse(urllib.urlopen(base_url))
		  sections = xml_sections.getElementsByTagName('Directory')
		  for s in sections:
		    if s.getAttribute('type') == source_type:
		      url = refresh_url % s.getAttribute('key')
		      x = urllib.urlopen(url)
		except Exception as e:
		  print "Unable to refresh plex, check your settings"
		  print e
