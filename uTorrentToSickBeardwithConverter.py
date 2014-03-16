import os
import sys
import autoProcessTV
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4

#Args: %L %T %D %K %F   Label, Tracker, Directory, single|multi, NameofFile(if single)

path = str(sys.argv[3])
settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
delete_dir = False
settings.delete = False
if not settings.output_dir:
    settings.output_dir = os.path.join(path, 'converted')
    if not os.path.exists(settings.output_dir):
        os.mkdir(settings.output_dir)
    delete_dir = True

converter = MkvtoMp4(settings)
    
if str(sys.argv[4]) == 'single':
    inputfile = os.path.join(path,str(sys.argv[5]))
    if MkvtoMp4(settings).validSource(inputfile):
        converter.process(inputfile)
else:
    for r, d, f in os.walk(path):
        for files in f:
            inputfile = os.path.join(r, files)
            if MkvtoMp4(settings).validSource(inputfile):
                converter.process(inputfile)

autoProcessTV.processEpisode(converter.output_dir)
if os.path.exists(settings.output_dir) and delete_dir:
    try:
        os.rmdir(converter.output_dir)
    except:
        print "Unable to delete temporary conversion directory"
