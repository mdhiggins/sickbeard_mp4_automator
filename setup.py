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
        "Automatically convert video files to a standardized format with mp4 metadata tagging to create a beautiful and uniform media library."),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mdhiggins/sickbeard_mp4_automator",
    keywords="ffmpeg media conversion sonarr radarr sickbeard mp4 sickrage couchpotato deluge qbittorrent metadata utorrent sab sabnzbd nzbget multimedia video mkv",
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
        'requests'
        'requests[security]',
        'requests-cache',
        'babelfish',
        'tmdbsimple',
        'mutagen',
        'guessit',
        'subliminal',
        'python-dateutil',
        'stevedore',
        'qtfaststart',
    ],
    extras_require={
        "deluge": ["deluge-client", "gevent"],
        "qbittorrent": ["python-qbittorrent"],
    }
)
