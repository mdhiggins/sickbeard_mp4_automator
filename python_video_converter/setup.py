#!/usr/bin/env python

from distutils.core import setup, Command
from unittest import TextTestRunner, TestLoader
import os
import os.path

class TestCommand(Command):
    user_options = []

    def initialize_options(self):
        self._testdir = os.path.join(os.getcwd(), 'test')

    def finalize_options(self):
        pass

    def run(self):
        os.chdir(self._testdir)
        retval = os.system('python -m test')
        if retval != 0:
            raise Exception('tests failed')

class DocCommand(Command):
    user_options = []

    def initialize_options(self):
        self._docdir = os.path.join(os.getcwd(), 'doc')

    def finalize_options(self):
        pass

    def run(self):
        os.chdir(self._docdir)
        os.system('make html')

setup(
    name = 'VideoConverter',
    version = '1.0.2',
    description = 'Video Converter library',
    url = 'http://senko.net/en/',

    author = 'Senko Rasic',
    author_email = 'senko.rasic@dobarkod.hr',

    cmdclass = {
        'test': TestCommand,
        'doc': DocCommand
    },

    packages = [ 'converter' ],
)
