#!/usr/bin/python

import os
import subprocess

def main():
	print 'sample: main'
	if os.name != 'posix':
		print "You can't add file to iTunes this way unless you are using OSX"
		return
	if not os.environ.get('output'):
		return
	final_destination = os.environ.get('output')
	if os.environ.get('moveto'):
		final_destination = os.environ.get('moveto')
	print 'final destination: ' + final_destination

	current_directory = os.path.dirname(os.path.realpath(__file__))
	add_to_itunes_script_path = os.path.join(current_directory, 'resources', 'add_to_itunes.scpt')

	if not os.path.exists(final_destination):
		print 'The file you are trying to add to iTunes at ' + str(final_destination) + ' does not exist'
		return
	try:
		subprocess.call(['osascript', add_to_itunes_script_path, final_destination])
		print 'Added to iTunes'
	except Exception as e:
		print 'Exception on adding to iTunes this file %s' % (final_destination)
		print e


if __name__ == "__main__":
    main()