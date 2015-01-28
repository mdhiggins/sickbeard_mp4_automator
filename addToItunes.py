#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
addToItunes.py
~~~~~~~~

This module returns the preferred location of the add to itunes AppleScript

This has relative location of add_to_itunes.scpt AppleScript. This AppleScript
can add a movie or television show to iTunes without having to copy the file or
move it, or playing it in iTunes immediately.
"""

import os.path


def where():
    """Return the location of add to itunes AppleScript."""
    # vendored bundle inside Requests
    return os.path.join(os.path.dirname(__file__), 'add_to_itunes.scpt')

if __name__ == '__main__':
    print(where())
