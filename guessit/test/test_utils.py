#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2013 Nicolas Wack <wackou@gmail.com>
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

from __future__ import absolute_import, division, print_function, unicode_literals

from guessit.test.guessittest import *
from guessit.fileutils import split_path
from guessit.textutils import strip_brackets, str_replace, str_fill, from_camel, is_camel,\
    levenshtein, reorder_title
from guessit import PY2
from guessit.date import search_date, search_year
from datetime import datetime, date, timedelta


class TestUtils(TestGuessit):
    def test_splitpath(self):
        alltests = {False: {'/usr/bin/smewt': ['/', 'usr', 'bin', 'smewt'],
                                           'relative_path/to/my_folder/': ['relative_path', 'to', 'my_folder'],
                                           '//some/path': ['//', 'some', 'path'],
                                           '//some//path': ['//', 'some', 'path'],
                                           '///some////path': ['///', 'some', 'path']

                                             },
                     True: {'C:\\Program Files\\Smewt\\smewt.exe': ['C:\\', 'Program Files', 'Smewt', 'smewt.exe'],
                                  'Documents and Settings\\User\\config': ['Documents and Settings', 'User', 'config'],
                                  'C:\\Documents and Settings\\User\\config': ['C:\\', 'Documents and Settings', 'User', 'config'],
                                  # http://bugs.python.org/issue19945
                                  '\\\\netdrive\\share': ['\\\\', 'netdrive', 'share'] if PY2 else ['\\\\netdrive\\share'],
                                  '\\\\netdrive\\share\\folder': ['\\\\', 'netdrive', 'share', 'folder'] if PY2 else ['\\\\netdrive\\share\\', 'folder'],
                                  }
                     }
        tests = alltests[sys.platform == 'win32']
        for path, split in tests.items():
            self.assertEqual(split, split_path(path))

    def test_strip_brackets(self):
        allTests = (('', ''),
                    ('[test]', 'test'),
                    ('{test2}', 'test2'),
                    ('(test3)', 'test3'),
                    ('(test4]', '(test4]'),
                    )

        for i, e in allTests:
            self.assertEqual(e, strip_brackets(i))

    def test_levenshtein(self):
        self.assertEqual(levenshtein("abcdef ghijk lmno", "abcdef ghijk lmno"), 0)
        self.assertEqual(levenshtein("abcdef ghijk lmnop", "abcdef ghijk lmno"), 1)
        self.assertEqual(levenshtein("abcdef ghijk lmno", "abcdef ghijk lmn"), 1)
        self.assertEqual(levenshtein("abcdef ghijk lmno", "abcdef ghijk lmnp"), 1)
        self.assertEqual(levenshtein("abcdef ghijk lmno", "abcdef ghijk lmnq"), 1)
        self.assertEqual(levenshtein("cbcdef ghijk lmno", "abcdef ghijk lmnq"), 2)
        self.assertEqual(levenshtein("cbcdef ghihk lmno", "abcdef ghijk lmnq"), 3)

    def test_reorder_title(self):
        self.assertEqual(reorder_title("Simpsons, The"), "The Simpsons")
        self.assertEqual(reorder_title("Simpsons,The"), "The Simpsons")
        self.assertEqual(reorder_title("Simpsons,Les", articles=('the', 'le', 'la', 'les')), "Les Simpsons")
        self.assertEqual(reorder_title("Simpsons, Les", articles=('the', 'le', 'la', 'les')), "Les Simpsons")

    def test_camel(self):
        self.assertEqual("", from_camel(""))

        self.assertEqual("Hello world", str_replace("Hello World", 6, 'w'))
        self.assertEqual("Hello *****", str_fill("Hello World", (6, 11), '*'))

        self.assertTrue("This is camel", from_camel("ThisIsCamel"))

        self.assertEqual('camel case', from_camel('camelCase'))
        self.assertEqual('A case', from_camel('ACase'))
        self.assertEqual('MiXedCaSe is not camel case', from_camel('MiXedCaSe is not camelCase'))

        self.assertEqual("This is camel cased title", from_camel("ThisIsCamelCasedTitle"))
        self.assertEqual("This is camel CASED title", from_camel("ThisIsCamelCASEDTitle"))

        self.assertEqual("These are camel CASED title", from_camel("TheseAreCamelCASEDTitle"))

        self.assertEqual("Give a camel case string", from_camel("GiveACamelCaseString"))

        self.assertEqual("Death TO camel case", from_camel("DeathTOCamelCase"))
        self.assertEqual("But i like java too:)", from_camel("ButILikeJavaToo:)"))

        self.assertEqual("Beatdown french DVD rip.mkv", from_camel("BeatdownFrenchDVDRip.mkv"))
        self.assertEqual("DO NOTHING ON UPPER CASE", from_camel("DO NOTHING ON UPPER CASE"))

        self.assertFalse(is_camel("this_is_not_camel"))
        self.assertTrue(is_camel("ThisIsCamel"))

        self.assertEqual("Dark.City.(1998).DC.BDRIP.720p.DTS.X264-CHD.mkv", from_camel("Dark.City.(1998).DC.BDRIP.720p.DTS.X264-CHD.mkv"))
        self.assertFalse(is_camel("Dark.City.(1998).DC.BDRIP.720p.DTS.X264-CHD.mkv"))

        self.assertEqual("A2LiNE", from_camel("A2LiNE"))

    def test_date(self):
        self.assertEqual(search_year(' in the year 2000... '), (2000, (13, 17)))
        self.assertEqual(search_year(' they arrived in 1492. '), (None, None))

        today = date.today()
        today_year_2 = int(str(today.year)[2:])

        future = today + timedelta(days=1000)
        future_year_2 = int(str(future.year)[2:])

        past = today - timedelta(days=10000)
        past_year_2 = int(str(past.year)[2:])

        self.assertEqual(search_date(' Something before 2002-04-22 '), (date(2002, 4, 22), (18, 28)))
        self.assertEqual(search_date(' 2002-04-22 Something after '), (date(2002, 4, 22), (1, 11)))

        self.assertEqual(search_date(' This happened on 2002-04-22. '), (date(2002, 4, 22), (18, 28)))
        self.assertEqual(search_date(' This happened on 22-04-2002. '), (date(2002, 4, 22), (18, 28)))

        self.assertEqual(search_date(' This happened on 13-04-%s. ' % (today_year_2,)), (date(today.year, 4, 13), (18, 26)))
        self.assertEqual(search_date(' This happened on 22-04-%s. ' % (future_year_2,)), (date(future.year, 4, 22), (18, 26)))
        self.assertEqual(search_date(' This happened on 20-04-%s. ' % (past_year_2)), (date(past.year, 4, 20), (18, 26)))

        self.assertEqual(search_date(' This happened on 13-06-14. ', year_first=True), (date(2013, 6, 14), (18, 26)))
        self.assertEqual(search_date(' This happened on 13-05-14. ', year_first=False), (date(2014, 5, 13), (18, 26)))

        self.assertEqual(search_date(' This happened on 04-13-%s. ' % (today_year_2,)), (date(today.year, 4, 13), (18, 26)))
        self.assertEqual(search_date(' This happened on 04-22-%s. ' % (future_year_2,)), (date(future.year, 4, 22), (18, 26)))
        self.assertEqual(search_date(' This happened on 04-20-%s. ' % (past_year_2)), (date(past.year, 4, 20), (18, 26)))

        self.assertEqual(search_date(' This happened on 35-12-%s. ' % (today_year_2,)), (None, None))
        self.assertEqual(search_date(' This happened on 37-18-%s. ' % (future_year_2,)), (None, None))
        self.assertEqual(search_date(' This happened on 44-42-%s. ' % (past_year_2)), (None, None))

        self.assertEqual(search_date(' This happened on %s. ' % (today, )), (today, (18, 28)))
        self.assertEqual(search_date(' This happened on %s. ' % (future, )), (future, (18, 28)))
        self.assertEqual(search_date(' This happened on %s. ' % (past, )), (past, (18, 28)))

        self.assertEqual(search_date(' released date: 04-03-1901? '), (None, None))

        self.assertEqual(search_date(' There\'s no date in here. '), (None, None))

        self.assertEqual(search_date(' Something 01-02-03 '), (date(2003, 2, 1), (11, 19)))
        self.assertEqual(search_date(' Something 01-02-03 ', year_first=False, day_first=True), (date(2003, 2, 1), (11, 19)))
        self.assertEqual(search_date(' Something 01-02-03 ', year_first=True), (date(2001, 2, 3), (11, 19)))
        self.assertEqual(search_date(' Something 01-02-03 ', day_first=False), (date(2003, 1, 2), (11, 19)))


suite = allTests(TestUtils)

if __name__ == '__main__':
    TextTestRunner(verbosity=2).run(suite)
