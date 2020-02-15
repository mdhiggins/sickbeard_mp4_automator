import logging
import os
import sys
from logging.config import fileConfig


def getLogger(name=None, custompath=None):
    logpath = '/var/log/sickbeard_mp4_automator'
    if os.name == 'nt':
        logpath = custompath if custompath else os.path.dirname(sys.argv[0])
    elif not os.path.isdir(logpath):
        try:
            os.mkdir(logpath)
        except:
            logpath = os.path.dirname(sys.argv[0])

    configPath = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), 'logging.ini')).replace("\\", "\\\\")
    logPath = os.path.abspath(os.path.join(logpath, 'index.log')).replace("\\", "\\\\")
    fileConfig(configPath, defaults={'logfilename': logPath})
    return logging.getLogger(name)
