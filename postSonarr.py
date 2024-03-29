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


# Sonarr API functions
def rescanRequest(baseURL, headers, seriesid, log):
    url = baseURL + "/api/v3/command"
    log.debug("Queueing rescan command to Sonarr via %s." % url)

    # First trigger rescan
    payload = {'name': 'RescanSeries', 'seriesId': seriesid}
    log.debug(str(payload))

    r = requests.post(url, json=payload, headers=headers)
    rstate = r.json()
    try:
        rstate = rstate[0]
    except:
        pass
    log.debug(str(rstate))
    log.info("Sonarr response from RescanSeries command: ID %d %s." % (rstate['id'], rstate['status']))
    return rstate


def waitForCommand(baseURL, headers, commandID, log, retries=6, delay=10):
    url = baseURL + "/api/v3/command/" + str(commandID)
    log.debug("Requesting command status from Sonarr for command ID %d." % commandID)
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


def renameRequest(baseURL, headers, fileid, seriesid, log):
    url = baseURL + "/api/v3/command"
    log.debug("Queueing rename command to Sonarr via %s." % url)

    if fileid:
        payload = {'name': 'RenameFiles', 'files': [fileid], 'seriesId': seriesid}
    else:
        payload = {'name': 'RenameSeries', 'seriesIds': [seriesid]}

    log.debug(str(payload))
    r = requests.post(url, json=payload, headers=headers)
    rstate = r.json()
    try:
        rstate = rstate[0]
    except:
        pass
    log.debug(str(rstate))
    log.info("Sonarr response from Rename command: ID %d %s." % (rstate['id'], rstate['status']))
    return rstate


def downloadedEpisodesScanInProgress(baseURL, headers, episodefile_sourcefolder, log):
    url = baseURL + "/api/v3/command"
    log.debug("Requesting commands in process from Sonarr via %s." % url)
    r = requests.get(url, headers=headers)
    commands = r.json()
    log.debug(commands)
    log.debug(episodefile_sourcefolder)
    for c in commands:
        try:
            if c.get('name') == "DownloadedEpisodesScan":
                if c['body']['path'] == episodefile_sourcefolder and c['status'] == 'started':
                    log.debug("Found a matching path scan in progress %s." % (episodefile_sourcefolder))
                    return c['id']
        except:
            pass
    log.debug("No commands in progress for %s." % (episodefile_sourcefolder))
    return None


def getEpisode(baseURL, headers, episodeid, log):
    url = baseURL + "/api/v3/episode/" + str(episodeid)
    log.debug("Requesting episode from Sonarr via %s." % url)
    r = requests.get(url, headers=headers)
    payload = r.json()
    log.debug(str(payload))
    return payload


def updateEpisode(baseURL, headers, new, episodeid, log):
    url = baseURL + "/api/v3/episode/" + str(episodeid)
    log.debug("Requesting episode update to Sonarr via %s." % url)
    r = requests.put(url, json=new, headers=headers)
    payload = r.json()
    return payload


def getEpisodeFile(baseURL, headers, episodefileid, log):
    url = baseURL + "/api/v3/episodefile/" + str(episodefileid)
    log.debug("Requesting episodefile from Sonarr for episodefile via %s." % url)
    r = requests.get(url, headers=headers)
    payload = r.json()
    return payload


def updateEpisodeFile(baseURL, headers, new, episodefileid, log):
    url = baseURL + "/api/v3/episodefile/" + str(episodefileid)
    log.debug("Requesting episodefile update to Sonarr via %s." % url)
    r = requests.put(url, json=new, headers=headers)
    payload = r.json()
    return payload


# Rename functions
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


def restoreSceneName(inputfile, scenename):
    if scenename:
        directory = os.path.dirname(inputfile)
        extension = os.path.splitext(inputfile)[1]
        os.rename(inputfile, os.path.join(directory, "%s%s" % (scenename, extension)))


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


log = getLogger("SonarrPostProcess")

log.info("Sonarr extra script post processing started.")

if os.environ.get('sonarr_eventtype') == "Test":
    log.info("Successful postSonarr.py SMA test, exiting.")
    sys.exit(0)

if os.environ.get('sonarr_eventtype') != "Download":
    log.error("Invalid event type %s, script only works for On Download/On Import and On Upgrade." % (os.environ.get('sonarr_eventtype')))
    sys.exit(1)

try:
    settings = ReadSettings()

    log.debug(os.environ)

    inputfile = os.environ.get('sonarr_episodefile_path')
    original = os.environ.get('sonarr_episodefile_scenename')
    tvdb_id = int(os.environ.get('sonarr_series_tvdbid'))
    imdb_id = os.environ.get('sonarr_series_imdbid')
    season = int(os.environ.get('sonarr_episodefile_seasonnumber'))
    seriesid = int(os.environ.get('sonarr_series_id'))
    scenename = os.environ.get('sonarr_episodefile_scenename')
    releasegroup = os.environ.get('sonarr_episodefile_releasegroup')
    episodefile_id = os.environ.get('sonarr_episodefile_id')
    episodefile_sourcefolder = os.environ.get('sonarr_episodefile_sourcefolder')
    episode = int(os.environ.get('sonarr_episodefile_episodenumbers').split(",")[0])
    episodeid = int(os.environ.get('sonarr_episodefile_episodeids').split(",")[0])
except:
    log.exception("Error reading environment variables")
    sys.exit(1)

mp = MediaProcessor(settings)

if settings.Sonarr.get('blockreprocess'):
    log.debug("Block reprocess enabled for Sonarr")
    settings.process_same_extensions = False

log.debug("Input file: %s." % inputfile)
log.debug("Original name: %s." % original)
log.debug("TVDB ID: %s." % tvdb_id)
log.debug("Season: %s episode: %s." % (season, episode))
log.debug("Sonarr series ID: %d." % seriesid)

try:
    if settings.Sonarr.get('rename'):
        # Prevent asynchronous errors from file name changing
        mp.settings.waitpostprocess = True
        try:
            inputfile = renameFile(inputfile, log)
        except:
            log.exception("Error renaming inputfile.")

    success = mp.fullprocess(inputfile, MediaType.TV, tvdbid=tvdb_id, imdbid=imdb_id, season=season, episode=episode, original=original, post=False)

    if not success:
        log.error("Processing returned False.")
        sys.exit(1)

    if success and not settings.Sonarr['rescan']:
        log.info("File processed successfully and rescan API update disabled.")
        sys.exit(0)

    # Update Sonarr to continue monitored status
    try:
        host = settings.Sonarr['host']
        port = settings.Sonarr['port']
        webroot = settings.Sonarr['webroot']
        apikey = settings.Sonarr['apikey']
        ssl = settings.Sonarr['ssl']
        protocol = "https://" if ssl else "http://"
        baseURL = protocol + host + ":" + str(port) + webroot

        log.debug("Sonarr baseURL: %s." % baseURL)
        log.debug("Sonarr apikey: %s." % apikey)

        if not apikey:
            log.error("Your Sonarr API Key is blank. Update autoProcess.ini to enable status updates.")
            sys.exit(1)

        headers = {
            'X-Api-Key': apikey,
            'User-Agent': "SMA - postSonarr"
        }

        subs = backupSubs(success[0], mp, log)

        inProcess = settings.Sonarr['in-progress-check'] and downloadedEpisodesScanInProgress(baseURL, headers, episodefile_sourcefolder, log)
        if inProcess and not waitForCommand(baseURL, headers, inProcess, log):
            log.info("DownloadedEpisodesScan command is in process for this episode, timed out for rescan but will queue.")
            rescanRequest(baseURL, headers, seriesid, log)
            renameRequest(baseURL, headers, None, seriesid, log)
            mp.post(success, MediaType.TV, tvdbid=tvdb_id, imdbid=imdb_id, season=season, episode=episode)
            sys.exit(0)

        rescanCommand = rescanRequest(baseURL, headers, seriesid, log)
        if not waitForCommand(baseURL, headers, rescanCommand['id'], log):
            log.error("Rescan command timed out.")
            sys.exit(1)

        log.info("Rescan command completed.")

        sonarrepinfo = getEpisode(baseURL, headers, episodeid, log)
        if not sonarrepinfo:
            log.error("No valid episode information found, aborting.")
            sys.exit(1)

        if not sonarrepinfo.get('hasFile'):
            log.warning("Rescanned episode does not have a file, attempting second rescan.")
            rescanAgain = rescanRequest(baseURL, headers, seriesid, log)
            if waitForCommand(baseURL, headers, rescanAgain['id'], log):
                sonarrepinfo = getEpisode(baseURL, headers, episodeid, log)
                if not sonarrepinfo:
                    log.error("No valid episode information found, aborting.")
                    sys.exit(1)
                if not sonarrepinfo.get('hasFile'):
                    log.warning("Rescanned episode still does not have a file, will not set to monitored to prevent endless loop.")
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
            rescanFinal = rescanCommand(baseURL, headers, seriesid, log)
            waitForCommand(baseURL, headers, rescanFinal['id'], log)

        # Then set that episode to monitored
        try:
            sonarrepinfo['monitored'] = True
            sonarrepinfo = updateEpisode(baseURL, headers, sonarrepinfo, episodeid, log)
            log.info("Sonarr monitoring information updated for episode %s." % sonarrepinfo['title'])
        except:
            log.exception("Failed to restore monitored status to episode.")

        if scenename or releasegroup:
            log.debug("Trying to restore scene information.")
            try:
                mf = getEpisodeFile(baseURL, headers, sonarrepinfo['episodeFileId'], log)
                mf['sceneName'] = scenename
                mf['releaseGroup'] = releasegroup
                mf = updateEpisodeFile(baseURL, headers, mf, sonarrepinfo['episodeFileId'], log)
                if scenename:
                    log.debug("Restored sceneName to %s." % mf.get('sceneName'))
                if releasegroup:
                    log.debug("Restored releaseGroup to %s." % mf.get('releaseGroup'))
            except:
                log.exception("Unable to restore scene information.")

        # Now a final rename step to ensure all release / codec information is accurate
        try:
            renameCommand = renameRequest(baseURL, headers, sonarrepinfo['episodeFileId'], seriesid, log)
            if waitForCommand(baseURL, headers, renameCommand['id'], log):
                finalEpisodeFile = getEpisodeFile(baseURL, headers, sonarrepinfo['episodeFileId'], log)
                success[0] = finalEpisodeFile.get("path", success[0])
        except:
            log.exception("Failed to trigger Sonarr rename.")
        mp.post(success, MediaType.TV, tvdbid=tvdb_id, imdbid=imdb_id, season=season, episode=episode)

    except:
        log.exception("Sonarr monitor status update failed.")
except:
    log.exception("Error processing file.")
    sys.exit(1)
