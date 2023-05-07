# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.


import sys
try:
    from urllib.request import FancyURLopener
    from urllib.parse import urlencode
except ImportError:
    from urllib import FancyURLopener
    from urllib import urlencode
import os
import logging


class AuthURLOpener(FancyURLopener):
    def __init__(self, user, pw):
        self.username = user
        self.password = pw
        self.numTries = 0
        FancyURLopener.__init__(self)

    def prompt_user_passwd(self, host, realm):
        if self.numTries == 0:
            self.numTries = 1
            return (self.username, self.password)
        else:
            return ('', '')

    def openit(self, url):
        self.numTries = 0
        return FancyURLopener.open(self, url)


def processEpisode(dirName, settings, nzbName=None, logger=None, pathMapping={}):
    log = logger or logging.getLogger(__name__)

    # Path Mapping
    targetdirs = dirName.split(os.sep)
    for k in sorted(pathMapping.keys(), reverse=True):
        mapdirs = k.split(os.sep)
        if mapdirs == targetdirs[:len(mapdirs)]:
            dirName = os.path.join(pathMapping[k], os.path.relpath(dirName, k))
            log.debug("PathMapping match found, replacing %s with %s, final directory is %s." % (k, pathMapping[k], dirName))
            break

    host = settings.Sickbeard['host']
    port = settings.Sickbeard['port']
    username = settings.Sickbeard['user']
    password = settings.Sickbeard['pass']
    try:
        ssl = int(settings.Sickbeard['ssl'])
    except:
        ssl = 0

    try:
        webroot = settings.Sickbeard['webroot']
    except:
        webroot = ""

    params = {}

    params['quiet'] = 1

    params['dir'] = dirName
    if nzbName is not None:
        params['nzbName'] = nzbName

    myOpener = AuthURLOpener(username, password)

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    url = protocol + host + ":" + str(port) + webroot + "/home/postprocess/processEpisode?" + urlencode(params)

    log.debug('Host: %s.' % host)
    log.debug('Port: %s.' % port)
    log.debug('Username: %s.' % username)
    log.debug('Password: %s.' % password)
    log.debug('Protocol: %s.' % protocol)
    log.debug('Web Root: %s.' % webroot)
    log.debug('URL: %s.' % url)

    log.info("Opening URL: %s." % url)

    try:
        urlObj = myOpener.openit(url)
    except IOError:
        log.exception("Unable to open URL")
        sys.exit(1)

    result = urlObj.readlines()
    lastline = None

    for line in result:
        if line:
            log.debug(line.strip())
            lastline = line.strip()

    if lastline:
        log.info(lastline)
