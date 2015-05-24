#!/usr/bin/python

import os

def main():
	print 'sample: main'
	if not os.environ.get('output'):
		return
	print os.environ.get('output')
	

if __name__ == "__main__":
    main()