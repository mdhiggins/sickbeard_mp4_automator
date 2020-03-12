import logging
import os
import sys
from logging.config import fileConfig


def getLogger(name=None, custompath=None):
    if custompath:
        custompath = os.path.realpath(custompath)
        if not os.path.isdir(custompath):
            custompath = os.path.dirname(custompath)
        rootpath = os.path.abspath(custompath)
        resourcepath = os.path.join(rootpath, "resources")
        configpath = os.path.join(rootpath, "config")
    else:
        resourcepath = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
        rootpath = os.path.abspath(os.path.join(resourcepath, "../"))
        configpath = os.path.join(rootpath, "config")

    loglocal = os.environ.get("SMA_LOGLOCAL", "false").lower() in ['true', 'yes', 't', '1', 'y']
    if os.name == 'nt' or loglocal:
        logpath = configpath
    else:
        logpath = '/var/log'

    if not os.path.isdir(logpath):
        try:
            os.mkdir(logpath)
        except:
            logpath = configpath

    configfile = os.path.abspath(os.path.join(resourcepath, 'logging.ini')).replace("\\", "\\\\")
    logfile = os.path.abspath(os.path.join(logpath, 'sma.log')).replace("\\", "\\\\")
    fileConfig(configfile, defaults={'logfilename': logfile})

    return logging.getLogger(name)
