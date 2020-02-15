import logging
import os
import sys
from logging.config import fileConfig


def getLogger(name=None, custompath=None):
    if custompath:
        if not os.path.isdir(custompath):
            custompath = os.path.dirname(custompath)
        custompath = os.path.realpath(custompath)

    logpath = '/var/log/sickbeard_mp4_automator'

    rootpath = os.path.dirname(sys.argv[0])
    rootpath = os.path.realpath(rootpath)

    if os.name == 'nt':
        logpath = custompath if custompath else rootpath
        logpath = os.path.realpath(logpath)
    elif not os.path.isdir(logpath):
        try:
            os.mkdir(logpath)
        except:
            logpath = rootpath

    configPath = os.path.abspath(os.path.join(custompath if custompath else rootpath, 'logging.ini')).replace("\\", "\\\\")
    logPath = os.path.abspath(os.path.join(logpath, 'index.log')).replace("\\", "\\\\")
    fileConfig(configPath, defaults={'logfilename': logPath})
    return logging.getLogger(name)
