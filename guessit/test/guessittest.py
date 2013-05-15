#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2011 Nicolas Wack <wackou@gmail.com>
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
from guessit import base_text_type, u
from guessit.slogging import setupLogging
from unittest import TestCase, TestLoader, TextTestRunner

import yaml, logging, sys, os
from os.path import *

MAIN_LOGGING_LEVEL = logging.INFO


def currentPath():
    '''Returns the path in which the calling file is located.'''
    return dirname(join(os.getcwd(), sys._getframe(1).f_globals['__file__']))

def addImportPath(path):
    '''Function that adds the specified path to the import path. The path can be
    absolute or relative to the calling file.'''
    importPath = abspath(join(currentPath(), path))
    sys.path = [ importPath ] + sys.path



setupLogging()
logging.getLogger().setLevel(MAIN_LOGGING_LEVEL)

log = logging.getLogger(__name__)


import guessit
from guessit import *
from guessit.matcher import *
from guessit.fileutils import *

def allTests(testClass):
    return TestLoader().loadTestsFromTestCase(testClass)


class TestGuessit(TestCase):

    def checkMinimumFieldsCorrect(self, filetype, filename, remove_type=True,
                                  exclude_files=None):
        groundTruth = yaml.load(load_file_in_same_dir(__file__, filename))
        def guess_func(string):
            return guess_file_info(string, filetype=filetype)

        return self.checkFields(groundTruth, guess_func, remove_type, exclude_files)


    def checkFields(self, groundTruth, guess_func, remove_type=True,
                    exclude_files=None):
        correct, total = 0, 0
        exclude_files = exclude_files or []

        for filename, required_fields in groundTruth.items():
            filename = u(filename)
            if filename in exclude_files:
                continue

            log.debug('\n' + '-' * 120)
            log.info('Guessing information for file: %s' % filename)

            found = guess_func(filename)

            total = total + 1
            is_incomplete = [False]

            def error(*args):
                log.warning(args[0] % args[1:])
                is_incomplete[0] = True

            # no need for these in the unittests
            if remove_type:
                try:
                    del found['type']
                except:
                    pass
            for prop in ('container', 'mimetype'):
                if prop in found:
                    del found[prop]

            # props which are list of just 1 elem should be opened for easier writing of the tests
            for prop in ('language', 'subtitleLanguage', 'other'):
                value = found.get(prop, None)
                if isinstance(value, list) and len(value) == 1:
                    found[prop] = value[0]

            # look for missing properties
            for prop, value in required_fields.items():
                if prop not in found:
                    error("Prop '%s' not found in: %s", prop, filename)
                    continue

                # if both properties are strings, do a case-insensitive comparison
                if (isinstance(value, base_text_type) and
                    isinstance(found[prop], base_text_type)):
                    if value.lower() != found[prop].lower():
                        error("Wrong prop value [str] for '%s': expected = '%s' - received = '%s'",
                              prop, u(value), u(found[prop]))

                # if both are lists, we assume list of strings and do a case-insensitive
                # comparison on their elements
                elif isinstance(value, list) and isinstance(found[prop], list):
                    s1 = set(u(s).lower() for s in value)
                    s2 = set(u(s).lower() for s in found[prop])
                    if s1 != s2:
                        error("Wrong prop value [list] for '%s': expected = '%s' - received = '%s'",
                              prop, u(value), u(found[prop]))
                # otherwise, just compare their values directly
                else:
                    if found[prop] != value:
                        error("Wrong prop value for '%s': expected = '%s' [%s] - received = '%s' [%s]",
                              prop, u(value), type(value), u(found[prop]), type(found[prop]))

            # look for additional properties
            for prop, value in found.items():
                if prop not in required_fields:
                    log.warning("Found additional info for prop = '%s': '%s'" % (prop, u(value)))

            if not is_incomplete[0]:
                correct = correct + 1

        log.info('SUMMARY: Guessed correctly %d out of %d filenames' % (correct, total))

        self.assertTrue(correct == total,
                        msg='Correct: %d < Total: %d' % (correct, total))