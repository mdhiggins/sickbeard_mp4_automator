#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:unlicense (http://unlicense.org/)


__author__ = "dbr/Ben"
__version__ = "2.0-dev"

import sys
import logging
import warnings

from tvdb_exceptions import tvdb_userabort

logging.getLogger(__name__).warning(
    "tvdb_ui module is deprecated - use classes directly from tvdb_api instead")

from tvdb_api import BaseUI, ConsoleUI
