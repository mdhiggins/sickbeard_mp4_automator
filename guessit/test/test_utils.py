#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2012 Nicolas Wack <wackou@gmail.com>
#
# GuessIt is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# GuessIt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


from guessittest import *
from guessit.fileutils import split_path

class TestUtils(TestGuessit):

    def test_splitpath(self):
        alltests = { ('linux2', 'darwin'): { '/usr/bin/smewt': ['/', 'usr', 'bin', 'smewt'],
                                             'relative_path/to/my_folder/': ['relative_path', 'to', 'my_folder'],
                                             '//some/path': ['/', 'some', 'path'],
                                             '//some//path': ['/', 'some', 'path'],
                                             '///some////path': ['/', 'some', 'path']

                                             },
                     ('win32',): { r'C:\Program Files\Smewt\smewt.exe': ['C:\\', 'Program Files', 'Smewt', 'smewt.exe'],
                                   r'Documents and Settings\User\config\\': ['Documents and Settings', 'User', 'config'],
                                   r'C:\Documents and Settings\User\config\\': ['C:\\', 'Documents and Settings', 'User', 'config'],
                                   r'\\netdrive\share': [r'\\', 'netdrive', 'share'],
                                   r'\\netdrive\share\folder': [r'\\', 'netdrive', 'share', 'folder']
                                   }
                     }
        for platforms, tests in alltests.items():
            if sys.platform in platforms:
                for path, split in tests.items():
                    self.assertEqual(split, split_path(path))


suite = allTests(TestUtils)

if __name__ == '__main__':
    TextTestRunner(verbosity=2).run(suite)
