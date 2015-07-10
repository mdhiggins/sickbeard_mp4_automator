from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
import traceback
import sys
import os

log = CPLog(__name__)

# Edit to point to the absolute path where the rest of the script resides
path = "C:\\Scripts\\"


class PostProcess(Plugin):

    def __init__(self):
        addEvent('renamer.after', self.callscript)


    def callscript(self, message = None, group = None):

        log.info('MP4 Automator - Post processing script initialized')

        sys.path.append(path)
        try:
            from readSettings import ReadSettings
            from mkvtomp4 import MkvtoMp4
            from tmdb_mp4 import tmdb_mp4
            from autoprocess import plex
            from post_processor import PostProcessor
        except ImportError:
            log.error('Path to script folder appears to be invalid.')
            return False

        settings = ReadSettings(path, "autoProcess.ini")
        converter = MkvtoMp4(settings)

        try:
            imdbid = group['library']['identifier']
        except:
            imdbid = group['identifier']

        moviefile = group['renamed_files']
        original = group['files']['movie'][0]

        success = False

        for inputfile in moviefile:
            try:
                log.info('Processing file: %s', inputfile)
                if MkvtoMp4(settings).validSource(inputfile):
                    log.info('File is valid')
                    output = converter.process(inputfile, original=original)

                    # Tag with metadata
                    if settings.tagfile:
                        log.info('Tagging file with IMDB ID %s', imdbid)
                        tagmp4 = tmdb_mp4(imdbid, original=original, language=settings.taglanguage)
                        tagmp4.setHD(output['x'], output['y'])
                        tagmp4.writeTags(output['output'], settings.artwork)

                    #QTFS
                    if settings.relocate_moov:
                        converter.QTFS(output['output'])

                    # Copy to additional locations
                    output_files = converter.replicate(output['output'])

                    # Run any post process scripts
                    if settings.postprocess:
                        post_processor = PostProcessor(output_files, log)
                        post_processor.setMovie(imdbid)
                        post_processor.run_scripts()

                    success = True
                else:
                    log.info('File is invalid')
            except:
                log.error('File processing failed: %s', (traceback.format_exc()))

        plex.refreshPlex(settings, 'movie', log)

        return success
