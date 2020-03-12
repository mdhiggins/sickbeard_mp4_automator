import logging
import os
import sys
from logging.config import fileConfig


def getLogger(name=None, custompath=None):
    if custompath:
        custompath = os.path.realpath(custompath)
        if not os.path.isdir(custompath):
            custompath = os.path.dirname(custompath)

    logpath = '/var/log/sickbeard_mp4_automator'

    rootpath = os.path.join(os.path.realpath(__file__))
    rootpath = os.path.dirname(rootpath)

    if os.name == 'nt':
        logpath = custompath or os.path.join(rootpath, "../")
    elif not os.path.isdir(logpath):
        try:
            os.mkdir(logpath)
        except:
            logpath = rootpath

    configPath = os.path.abspath(os.path.join(custompath or rootpath, 'logging.ini')).replace("\\", "\\\\")
    logPath = os.path.abspath(os.path.join(logpath, 'index.log')).replace("\\", "\\\\")
    fileConfig(configPath, defaults={'logfilename': logPath})
    return logging.getLogger(name)
