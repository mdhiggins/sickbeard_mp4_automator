Quicktime/MP4 Fast Start
------------------------
Enable streaming and pseudo-streaming of Quicktime and MP4 files by
moving metadata and offset information to the front of the file.

This program is based on qt-faststart.c from the ffmpeg project, which is
released into the public domain, as well as ISO 14496-12:2005 (the official
spec for MP4), which can be obtained from the ISO or found online.

The goals of this project are to run anywhere without compilation (in
particular, many Windows and Mac OS X users have trouble getting
qt-faststart.c compiled), to run about as fast as the C version, to be more
user friendly, and to use less actual lines of code doing so.

Features
--------

    * Works everywhere Python can be installed
    * Handles both 32-bit (stco) and 64-bit (co64) atoms
    * Handles any file where the mdat atom is before the moov atom
    * Preserves the order of other atoms
    * Can replace the original file (if given no output file)

Installing from PyPi
--------------------

To install from PyPi, you may use easy_install or pip::

    easy_install qtfaststart

Installing from source
----------------------

Download a copy of the source, ``cd`` into the top-level
``qtfaststart`` directory, and run::

    python setup.py install

If you are installing to your system Python (instead of a virtualenv), you
may need root access (via ``sudo`` or ``su``).

Usage
-----
See ``qtfaststart --help`` for more info! If outfile is not present then
the infile is overwritten.

    $ qtfaststart infile [outfile]

To run without installing you can use::

    $ bin/qtfaststart infile [outfile]

History
-------
    * 2011-11-01: Fix long-standing os.SEEK_CUR bug, version bump to 1.6
    * 2011-10-11: Packaged and published to PyPi by Greg Taylor
      <gtaylor AT duointeractive DOT com>, version bump to 1.5.
    * 2010-02-21: Add support for final mdat atom with zero size, patch by
      Dmitry Simakov <basilio AT j-vista DOT ru>, version bump to 1.4.
    * 2009-11-05: Added --sample option. Version bump to 1.3
    * 2009-03-13: Update to be more library-friendly by using logging module,
      rename fast_start => process, version bump to 1.2
    * 2008-10-04: Bug fixes, support multiple atoms of the same type, 
      version bump to 1.1
    * 2008-09-02: Initial release

License
-------
Copyright (C) 2008 - 2011  Daniel G. Taylor <dan@programmer-art.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
