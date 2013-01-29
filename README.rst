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

To install from PyPi, you may use ``easy_install`` or ``pip``::

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

To see a list of top-level atoms and their order in the file::

    $ bin/qtfaststart --list infile

History
-------
    * 2013-01-28: Support strange zero-name, zero-length atoms, re-license
      under the MIT license, version bump to 1.7
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
Copyright (C) 2008 - 2013  Daniel G. Taylor <dan@programmer-art.org>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
