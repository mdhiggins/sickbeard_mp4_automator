import os
import re
import sys
import shutil
import autoProcessTV, autoProcessMovie
from readSettings import ReadSettings
from mkvtomp4 import MkvtoMp4

#Args: %L %T %D %K %F %I Label, Tracker, Directory, single|multi, NameofFile(if single), InfoHash

def _authToken(session=None, host=None, username=None, password=None):
    auth = None
    if not session:
        session = requests.Session()
    response = session.get(host + "gui/token.html", auth=(username, password), verify=False, timeout=30)
    if response.status_code == 200:
        auth = re.search("<div.*?>(\S+)<\/div>", response.text).group(1)
    else:
        print "[uTorrent] Authentication Failed - Status Code " + response.status_code
        
    return auth,session

def _sendRequest(session, host='http://localhost:8080/', username=None, password=None, params=None, files=None, fnct=None):
    try:
        response = session.post(host + "gui/", auth=(username, password), params=params, files=files, timeout=30)
    except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
        print "[uTorrent] Problem sending command " + fnct +  " - " + str(e)
        return False
    
    if response.status_code == 200:
        return True
    
    print "[uTorrent] Problem sending command " + fnct + ", return code = " + str(response.status_code)
    return False
    
path = str(sys.argv[3])
settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")
label = sys.argv[1].lower()

categories = [settings.uTorrent['cp'], settings.uTorrent['sb'], settings.uTorrent['sonarr']]

if label not in categories:
    print "No valid label detected"
    sys.exit()

# Import requests
try:
    import requests
except ImportError:
    print "[ERROR] Python module REQUESTS is required. Install with 'pip install requests' then try again."
    sys.exit()

try:
    torrent_hash = sys.argv[6]
    web_ui = settings.uTorrentWebUI
except:
    web_ui = False

# Run a uTorrent action before conversion.
if web_ui:
    session = requests.Session()
    if session:
        auth,session = _authToken(session, settings.uTorrentHost, settings.uTorrentUsername, settings.uTorrentPassword)
        if auth and settings.uTorrentActionBefore:
            params = {'token': auth, 'action': settings.uTorrentActionBefore, 'hash': torrent_hash}
            _sendRequest(session, settings.uTorrentHost, settings.uTorrentUsername, settings.uTorrentPassword, params, None, "Before Function")

if settings.uTorrent['convert']:
    # Perform conversion.
    delete_dir = False
    settings.delete = False
    if not settings.output_dir:
        settings.output_dir = os.path.join(path, 'converted')
        if not os.path.exists(settings.output_dir):
            os.mkdir(settings.output_dir)
        delete_dir = True

    converter = MkvtoMp4(settings)
        
    if str(sys.argv[4]) == 'single':
        inputfile = os.path.join(path, str(sys.argv[5]))
        if MkvtoMp4(settings).validSource(inputfile):
            converter.process(inputfile, reportProgress=True)
    else:
        for r, d, f in os.walk(path):
            for files in f:
                inputfile = os.path.join(r, files)
                if MkvtoMp4(settings).validSource(inputfile):
                    converter.process(inputfile, reportProgress=True)

    path = converter.output_dir
else:
    newpath = os.path.join(path, 'tempcopy')
    if not os.path.exists(newpath):
        os.mkdir(newpath)
    if str(sys.argv[4]) == 'single':
        inputfile = os.path.join(path, str(sys.argv[5]))
        shutil.copy(inputfile, newpath)
    else:
        for r, d, f in os.walk(path):
            for files in f:
                inputfile = os.path.join(r, files)
                shutil.copy(inputfile, newpath)
    path = newpath

if label == categories[0]:
    autoProcessMovie.process(path, settings)
    if os.path.exists(settings.output_dir) and delete_dir:
        try:
            os.rmdir(converter.output_dir)
        except:
            print "Unable to delete temporary conversion directory"
elif label == categories[1]:
    autoProcessTV.processEpisode(path, settings)
    if os.path.exists(settings.output_dir) and delete_dir:
        try:
            os.rmdir(converter.output_dir)
        except:
            print "Unable to delete temporary conversion directory"
elif label == categories[2]:
    host = settings.Sonarr['host']
    port = settings.Sonarr['port']
    apikey = settings.Sonarr['apikey']
    if apikey == '':
        print "[WARNING] Your Sonarr API Key can not be blank. Update autoProcess.ini"
        sys.exit()
    try:
        ssl = int(settings.Sonarr['ssl'])
    except:
        ssl = 0
    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"
    url = protocol+host+":"+port+"/api/command"
    payload = {'name': 'downloadedepisodesscan','path': path}
    print "[INFO] Requesting Sonarr to scan folder '"+path+"'"
    headers = {'X-Api-Key': apikey}
    try:
        r = requests.post(url, data=json.dumps(payload), headers=headers)
        rstate = r.json()
        print "[INFO] Sonarr responds as "+rstate['state']+"."
    except:
        print "[WARNING] Update to Sonarr failed, check if Sonarr is running, autoProcess.ini for errors, or check install of python modules requests."
        sys.exit()

# Run a uTorrent action after conversion.
if web_ui: 
    if session and auth and settings.uTorrentActionAfter:
        params = {'token': auth, 'action': settings.uTorrentActionAfter, 'hash': torrent_hash}
        _sendRequest(session, settings.uTorrentHost, settings.uTorrentUsername, settings.uTorrentPassword, params, None, "After Function")

sys.exit()
