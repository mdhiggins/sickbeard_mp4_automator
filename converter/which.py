#!/usr/bin/env python
#
# A Python implementation of the handy `which' shell command, showing
# the full path to a command that's in your path.
#
# Written by: Senko Rasic <senko.rasic@dobarkod.hr>
#
# Released to Public Domain. Use it as you like.

import sys
import os
import os.path

def which(name):
    """
    Find the full path to a binary named 'name' that's located
    somewhere in the PATH. Returns the file path, or None if there's
    no executable binary in the PATH with that name.
    """
    path = os.environ.get('PATH', os.defpath)
    for d in path.split(':'):
        fpath = os.path.join(d, name)
        if os.path.exists(fpath) and os.access(fpath, os.X_OK):
            return fpath
    return None

if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: %s <command>\n" % sys.argv[0])
        sys.exit(-1)
    else:
        fpath = which(sys.argv[1])
        if fpath:
            print fpath
            sys.exit(0)
        else:
            sys.stderr.write("Not found in path\n")
            sys.exit(-1)
