from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from subprocess import Popen, PIPE
import traceback
import os

log = CPLog(__name__)

# Edit to point to the absolute path where the CPProcess.py script resides
path = "C:\\Scripts\\"


class PostProcess(Plugin):

    def __init__(self):
        addEvent('renamer.after', self.callscript)

    
    def callscript(self, message = None, group = None):
        log.info('MP4 Automator Post Processing script initialized')
        try:
            imdbid = group['library']['identifier']
        except:
            imdbid = group['identifier']

        moviefile = group['renamed_files']
        original = group['files']['movie'][0]
        
        command = ['python']
        command.append(os.path.join(path, 'CPProcess.py'))
        command.append(imdbid)
        command.append(original)
        for x in moviefile:
            command.append(x)

        log.info("Command generated: %s", command)
        try:
            p = Popen(command, stdout=PIPE)
            res = p.wait()
            if res == 0:
                log.info('PostProcess Script was called successfully')
                return True
            else:
                log.info('PostProcess Script returned an error code: %s', str(res))
                log.info(p.stdout.read())

        except:
            log.error('Failed to call script: %s', (traceback.format_exc()))


        return False
