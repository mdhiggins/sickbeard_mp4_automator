#!/usr/bin/env python

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sickbeard_mp4_automator",
    version="1.0",
    author="Michael Higgins",
    author_email="mdhiggins23@gmail.com",
    description=(
        "Automatically convert video files to a standardized mp4 format with "
        "proper metadata tagging to create a beautiful and uniform media "
        "library."),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mdhiggins/sickbeard_mp4_automator",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "Natural Language :: English",
        "Topic :: Multimedia :: Video :: Conversion",
    ],
    install_requires=[
        'requests[security]',
        'requests-cache',
        'babelfish',
        # to use manual.py (requires guessit version 1, version 2 is a
        # complete rewrite, still in alpha, and not backwards compatible)
        'guessit<2',
        # to enable automatically downloading subtitles
        'subliminal<2',
        # requires stevedore version 1.19.1. The version pin is required
        # because this will be automatically installed with subliminal
        'stevedore==1.19.1',
        # if you plan on using Deluge
        'deluge-client',
        # to enable moving moov atom
        'qtfaststart',
    ],
)
