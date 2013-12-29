#!/usr/bin/env python

import os
import sys
import autoProcessTV
import datetime
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4

def Log(msg, *args):
    s = msg % args
    print datetime.datetime.now().strftime('%Y-%m-%d %H:%M ') + s

print "Converting Entire Folder"
settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
path = str(sys.argv[1])
converter = MkvtoMp4(settings)
converter.output_dir = None
Log('Scanning folder [%s]', path)
for r, d, f in os.walk(path):
    for files in f:
        inputfile = os.path.join(r, files)
        if MkvtoMp4(settings).validSource(inputfile):
            Log('Converting [%s]', inputfile)
            output = converter.process(inputfile, True)
            if settings.relocate_moov:
                converter.QTFS(output['output'])
            if settings.copyto:
                converter.replicate(output['output'])
        else :
            Log('Skipped [%s]', inputfile)
            
