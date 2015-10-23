from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
import traceback
import os
import subprocess

log = CPLog(__name__)

# Edit to point to the absolute path where the rest of the script resides
path = "C:\\Scripts\\"


class PostProcess(Plugin):

    def __init__(self):
        addEvent('renamer.after', self.callscript)


    def callscript(self, message = None, group = None):

        log.info('MP4 Automator - Post processing script initialized')

        exec_me = os.path.join(path, "postCouchPotato.py")

        try:
            imdbid = group['library']['identifier']
        except:
            imdbid = group['identifier']

        moviefile = group['renamed_files']
        original = group['files']['movie'][0]

        success = True

        for inputfile in moviefile:
            try:
                subprocess.Popen([exec_me, imdbid, inputfile, original], shell = (os.name == 'nt'))
                log.info("Executing post processing on file %s" % inputfile)
            except:
                log.error("Failed to execute post processing on file %s" % inputfile)
                log.error(traceback.format_exc())
                success = False

        return success
