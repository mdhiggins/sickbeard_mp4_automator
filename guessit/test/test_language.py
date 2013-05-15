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

from __future__ import unicode_literals
from guessittest import *
import io

class TestLanguage(TestGuessit):

    def check_languages(self, languages, scheme=None):
        for lang1, lang2 in languages.items():
            self.assertEqual(Language(lang1, scheme=scheme),
                             Language(lang2, scheme=scheme))

    def test_addic7ed(self):
        languages = {'English': 'en',
                     'English (US)': 'en',
                     'English (UK)': 'en',
                     'Italian': 'it',
                     'Portuguese': 'pt',
                     'Portuguese (Brazilian)': 'pt',
                     'Romanian': 'ro',
                     'Español (Latinoamérica)': 'es',
                     'Español (España)': 'es',
                     'Spanish (Latin America)': 'es',
                     'Español': 'es',
                     'Spanish': 'es',
                     'Spanish (Spain)': 'es',
                     'French': 'fr',
                     'Greek': 'el',
                     'Arabic': 'ar',
                     'German': 'de',
                     'Croatian': 'hr',
                     'Indonesian': 'id',
                     'Hebrew': 'he',
                     'Russian': 'ru',
                     'Turkish': 'tr',
                     'Swedish': 'se',
                     'Czech': 'cs',
                     'Dutch': 'nl',
                     'Hungarian': 'hu',
                     'Norwegian': 'no',
                     'Polish': 'pl',
                     'Persian': 'fa'}

        self.check_languages(languages)

    def test_subswiki(self):
        languages = {'English (US)': 'en', 'English (UK)': 'en', 'English': 'en',
                     'French': 'fr', 'Brazilian': 'po', 'Portuguese': 'pt',
                     'Español (Latinoamérica)': 'es', 'Español (España)': 'es',
                     'Español': 'es', 'Italian': 'it', 'Català': 'ca'}

        self.check_languages(languages)

    def test_tvsubtitles(self):
        languages = {'English': 'en', 'Español': 'es', 'French': 'fr', 'German': 'de',
                     'Brazilian': 'br', 'Russian': 'ru', 'Ukrainian': 'ua', 'Italian': 'it',
                     'Greek': 'gr', 'Arabic': 'ar', 'Hungarian': 'hu', 'Polish': 'pl',
                     'Turkish': 'tr', 'Dutch': 'nl', 'Portuguese': 'pt', 'Swedish': 'sv',
                     'Danish': 'da', 'Finnish': 'fi', 'Korean': 'ko', 'Chinese': 'cn',
                     'Japanese': 'jp', 'Bulgarian': 'bg', 'Czech': 'cz', 'Romanian': 'ro'}

        self.check_languages(languages)

    def test_opensubtitles(self):
        opensubtitles_langfile = file_in_same_dir(__file__, 'opensubtitles_languages_2012_05_09.txt')
        langs = [ u(l).strip().split('\t') for l in io.open(opensubtitles_langfile, encoding='utf-8') ][1:]
        for lang in langs:
            # check that we recognize the opensubtitles language code correctly
            # and that we are able to output this code from a language
            self.assertEqual(lang[0], Language(lang[0], scheme='opensubtitles').opensubtitles)
            if lang[1]:
                # check we recognize the opensubtitles 2-letter code correctly
                self.check_languages({lang[0]: lang[1]}, scheme='opensubtitles')

    def test_tmdb(self):
        # examples from http://api.themoviedb.org/2.1/language-tags
        for lang in ['en-US', 'en-CA', 'es-MX', 'fr-PF']:
            self.assertEqual(lang, Language(lang).tmdb)


    def test_subtitulos(self):
        languages = {'English (US)': 'en', 'English (UK)': 'en', 'English': 'en',
                     'French': 'fr', 'Brazilian': 'po', 'Portuguese': 'pt',
                     'Español (Latinoamérica)': 'es', 'Español (España)': 'es',
                     'Español': 'es', 'Italian': 'it', 'Català': 'ca'}

        self.check_languages(languages)

    def test_thesubdb(self):
        languages = {'af': 'af', 'cs': 'cs', 'da': 'da', 'de': 'de', 'en': 'en', 'es': 'es', 'fi': 'fi',
                     'fr': 'fr', 'hu': 'hu', 'id': 'id', 'it': 'it', 'la': 'la', 'nl': 'nl', 'no': 'no',
                     'oc': 'oc', 'pl': 'pl', 'pt': 'pt', 'ro': 'ro', 'ru': 'ru', 'sl': 'sl', 'sr': 'sr',
                     'sv': 'sv', 'tr': 'tr'}

        self.check_languages(languages)

    def test_language_object(self):
        self.assertEqual(len(list(set([Language('qwerty'), Language('asdf')]))), 1)
        d = { Language('qwerty'): 7 }
        d[Language('asdf')] = 23
        self.assertEqual(d[Language('qwerty')], 23)

    def test_exceptions(self):
        self.assertEqual(Language('br'), Language('pt(br)'))

        # languages should be equal regardless of country
        self.assertEqual(Language('br'), Language('pt'))

        self.assertEqual(Language('unknown'), Language('und'))


suite = allTests(TestLanguage)

if __name__ == '__main__':
    TextTestRunner(verbosity=2).run(suite)
