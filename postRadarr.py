#!/usr/bin/env python3
import os
import sys
import requests
import time
import shutil
from resources.log import getLogger
from resources.readsettings import ReadSettings
from resources.metadata import MediaType
from resources.mediaprocessor import MediaProcessor


# Radarr API functions
def rescanRequest(baseURL, headers, movieid, log):
    url = baseURL + "/api/v3/command"
    log.debug("Queueing rescan command to Radarr via %s." % url)

    # First trigger rescan
    payload = {'name': 'RescanMovie', 'movieId': movieid}
    log.debug(str(payload))

    r = requests.post(url, json=payload, headers=headers)
    rstate = r.json()
    try:
        rstate = rstate[0]
    except:
        pass
    log.debug(str(rstate))
    log.info("Radarr response from RescanMovie command: ID %d %s." % (rstate['id'], rstate['status']))
    return rstate


def waitForCommand(baseURL, headers, commandID, log, retries=6, delay=10):
    url = baseURL + "/api/v3/command/" + str(commandID)
    log.debug("Requesting command status from Radarr for command ID %d." % commandID)
    r = requests.get(url, headers=headers)
    command = r.json()

    attempts = 0
    while command['status'].lower() not in ['complete', 'completed'] and attempts < retries:
        log.debug("Status: %s." % (command['status']))
        time.sleep(delay)
        r = requests.get(url, headers=headers)
        command = r.json()
        attempts += 1
    log.debug(str(command))
    log.debug("Final status: %s." % (command['status']))
    return command['status'].lower() in ['complete', 'completed']


def renameRequest(baseURL, headers, fileid, movieid, log):
    url = baseURL + "/api/v3/command"
    log.debug("Queueing rename command to Radarr via %s." % url)

    if fileid:
        payload = {'name': 'RenameFiles', 'files': [fileid], 'movieId': movieid}
    else:
        payload = {'name': 'RenameMovies', 'movieIds': [movieid]}
    log.debug(str(payload))
    r = requests.post(url, json=payload, headers=headers)
    rstate = r.json()
    try:
        rstate = rstate[0]
    except:
        pass
    log.debug(str(rstate))
    log.info("Radarr response from Rename command: ID %d %s." % (rstate['id'], rstate['status']))
    return rstate


def downloadedMoviesScanInProgress(baseURL, headers, moviefile_sourcefolder, log):
    url = baseURL + "/api/v3/command"
    log.debug("Requesting commands in process from Radarr via %s." % url)
    r = requests.get(url, headers=headers)
    commands = r.json()
    log.debug(commands)
    log.debug(moviefile_sourcefolder)
    for c in commands:
        if c.get('name') == "DownloadedMoviesScan":
            try:
                if c['body']['path'] == moviefile_sourcefolder and c['status'] == 'started':
                    log.debug("Found a matching path scan in progress %s." % (moviefile_sourcefolder))
                    return True
            except:
                pass
    log.debug("No commands in progress for %s." % (moviefile_sourcefolder))
    return False


def getMovie(baseURL, headers, movieid, log):
    url = baseURL + "/api/v3/movie/" + str(movieid)
    log.debug("Requesting movie from Radarr via %s." % url)
    r = requests.get(url, headers=headers)
    payload = r.json()
    return payload


def updateMovie(baseURL, headers, new, movieid, log):
    url = baseURL + "/api/v3/movie/" + str(movieid)
    log.debug("Requesting movie update to Radarr via %s." % url)
    r = requests.put(url, json=new, headers=headers)
    payload = r.json()
    return payload


def getMovieFile(baseURL, headers, moviefileid, log):
    url = baseURL + "/api/v3/moviefile/" + str(moviefileid)
    log.debug("Requesting moviefile from Radarr for moviefile via %s." % url)
    r = requests.get(url, headers=headers)
    payload = r.json()
    return payload


def updateMovieFile(baseURL, headers, new, moviefileid, log):
    url = baseURL + "/api/v3/moviefile/" + str(moviefileid)
    log.debug("Requesting moviefile update to Radarr via %s." % url)
    r = requests.put(url, json=new, headers=headers)
    payload = r.json()
    return payload


# Rename functions
def restoreSceneName(inputfile, scenename):
    if scenename:
        directory = os.path.dirname(inputfile)
        extension = os.path.splitext(inputfile)[1]
        os.rename(inputfile, os.path.join(directory, "%s%s" % (scenename, extension)))


def renameFile(inputfile, log):
    filename, fileext = os.path.splitext(inputfile)
    outputfile = "%s.rnm%s" % (filename, fileext)
    i = 2
    while os.path.isfile(outputfile):
        outputfile = "%s.rnm%d%s" % (filename, i, fileext)
        i += 1
    os.rename(inputfile, outputfile)
    log.debug("Renaming file %s to %s." % (inputfile, outputfile))
    return outputfile


def backupSubs(inputpath, mp, log, extension=".backup"):
    dirname, filename = os.path.split(inputpath)
    files = []
    output = {}
    for r, _, f in os.walk(dirname):
        for file in f:
            files.append(os.path.join(r, file))
    for filepath in files:
        if filepath.startswith(os.path.splitext(filename)[0]):
            info = mp.isValidSubtitleSource(filepath)
            if info:
                newpath = filepath + extension
                shutil.copy2(filepath, newpath)
                output[newpath] = filepath
                log.info("Copying %s to %s." % (filepath, newpath))
    return output


def restoreSubs(subs, log):
    for k in subs:
        try:
            os.rename(k, subs[k])
            log.info("Restoring %s to %s." % (k, subs[k]))
        except:
            os.remove(k)
            log.exception("Unable to restore %s, deleting." % (k))


log = getLogger("RadarrPostProcess")

log.info("Radarr extra script post processing started.")

if os.environ.get('radarr_eventtype') == "Test":
    log.info("Successful postRadarr.py SMA test, exiting.")
    sys.exit(0)

if os.environ.get('radarr_eventtype') != "Download":
    log.error("Invalid event type %s, script only works for On Download/On Import and On Upgrade." % (os.environ.get('radarr_eventtype')))
    sys.exit(1)

try:
    settings = ReadSettings()

    log.debug(os.environ)

    inputfile = os.environ.get('radarr_moviefile_path')
    original = os.environ.get('radarr_moviefile_scenename')
    imdbid = os.environ.get('radarr_movie_imdbid')
    tmdbid = os.environ.get('radarr_movie_tmdbid')
    movieid = int(os.environ.get('radarr_movie_id'))
    moviefileid = int(os.environ.get('radarr_moviefile_id'))
    scenename = os.environ.get('radarr_moviefile_scenename')
    releasegroup = os.environ.get('radarr_moviefile_releasegroup')
    moviefile_sourcefolder = os.environ.get('radarr_moviefile_sourcefolder')
except:
    log.exception("Error reading environment variables")
    sys.exit(1)

mp = MediaProcessor(settings)

if settings.Radarr.get('blockreprocess'):
    log.debug("Block reprocess enabled for Radarr")
    settings.process_same_extensions = False

log.debug("Input file: %s." % inputfile)
log.debug("Original name: %s." % original)
log.debug("IMDB ID: %s." % imdbid)
log.debug("TMDB ID: %s." % tmdbid)
log.debug("Radarr Movie ID: %d." % movieid)

try:
    if settings.Radarr.get('rename'):
        # Prevent asynchronous errors from file name changing
        mp.settings.waitpostprocess = True
        try:
            inputfile = renameFile(inputfile, log)
        except:
            log.exception("Error renaming inputfile.")

    success = mp.fullprocess(inputfile, MediaType.Movie, original=original, tmdbid=tmdbid, imdbid=imdbid, post=False)

    if not success:
        log.info("Processing returned False.")
        sys.exit(1)

    if success and not settings.Radarr['rescan']:
        log.info("File processed successfully and rescan API update disabled.")
        sys.exit(0)

    try:
        host = settings.Radarr['host']
        port = settings.Radarr['port']
        webroot = settings.Radarr['webroot']
        apikey = settings.Radarr['apikey']
        ssl = settings.Radarr['ssl']
        protocol = "https://" if ssl else "http://"
        baseURL = protocol + host + ":" + str(port) + webroot

        log.debug("Radarr baseURL: %s." % baseURL)
        log.debug("Radarr apikey: %s." % apikey)

        if not apikey:
            log.error("Your Radarr API Key is blank. Update autoProcess.ini to enable status updates.")
            sys.exit(1)

        headers = {
            'X-Api-Key': apikey,
            'User-Agent': "SMA - postRadarr"
        }

        subs = backupSubs(success[0], mp, log)

        if downloadedMoviesScanInProgress(baseURL, headers, moviefile_sourcefolder, log):
            log.info("DownloadedMoviesScan command is in process for this movie, cannot wait for rescan but will queue.")
            rescanRequest(baseURL, headers, movieid, log, retries=0)
            renameRequest(baseURL, headers, None, movieid, log)
            mp.post(success, MediaType.Movie, tmdbid=tmdbid, imdbid=imdbid)
            sys.exit(0)

        rescanCommand = rescanRequest(baseURL, headers, movieid, log)
        if not waitForCommand(baseURL, headers, rescanCommand['id'], log):
            log.error("Rescan command timed out.")
            sys.exit(1)

        log.info("Rescan command completed successfully.")

        movieinfo = getMovie(baseURL, headers, movieid, log)
        if not movieinfo:
            log.error("No valid movie information found, aborting.")
            sys.exit(1)

        if not movieinfo.get('hasFile'):
            log.warning("Rescanned movie does not have a file, attempting second rescan.")
            rescanAgain = rescanRequest(baseURL, headers, movieid, log)
            if waitForCommand(baseURL, headers, rescanAgain['id'], log):
                movieinfo = getMovie(baseURL, headers, movieid, log)
                if not movieinfo.get('hasFile'):
                    log.warning("Rescanned movie still does not have a file, will not set to monitored to prevent endless loop.")
                    sys.exit(1)
                else:
                    log.info("File found after second rescan.")
            else:
                log.error("Rescan command timed out.")
                restoreSubs(subs, log)
                sys.exit(1)

        if len(subs) > 0:
            log.debug("Restoring %d subs and triggering a final rescan." % (len(subs)))
            restoreSubs(subs, log)
            rescanFinal = rescanRequest(baseURL, headers, movieid, log)
            waitForCommand(baseURL, headers, rescanFinal['id'], log)

        # Then set that movie to monitored
        try:
            movieinfo['monitored'] = True
            movieinfo = updateMovie(baseURL, headers, movieinfo, movieid, log)
            log.debug(str(movieinfo))
            log.info("Radarr monitoring information updated for movie %s." % movieinfo['title'])
        except:
            log.exception("Failed to restore monitored status to movie.")

        if scenename or releasegroup:
            log.debug("Trying to restore scene information.")
            try:
                mf = getMovieFile(baseURL, headers, movieinfo['movieFile']['id'], log)
                mf['sceneName'] = scenename
                mf['releaseGroup'] = releasegroup
                mf = updateMovieFile(baseURL, headers, mf, movieinfo['movieFile']['id'], log)
                if scenename:
                    log.debug("Restored sceneName to %s." % mf.get('sceneName'))
                if releasegroup:
                    log.debug("Restored releaseGroup to %s." % mf.get('releaseGroup'))
            except:
                log.exception("Unable to restore scene information.")

        # Now a final rename step to ensure all release / codec information is accurate
        try:
            renameCommand = renameRequest(baseURL, headers, movieinfo['movieFile']['id'], movieid, log)
            waitForCommand(baseURL, headers, renameCommand['id'], log)
        except:
            log.exception("Failed to trigger Radarr rename.")
        mp.post(success, MediaType.Movie, tmdbid=tmdbid, imdbid=imdbid)
    except:
        log.exception("Radarr monitor status update failed.")

except:
    log.exception("Error processing file.")
    sys.exit(1)
