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
)
