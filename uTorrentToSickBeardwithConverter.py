import os
import re
import sys
import autoProcessTV
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
        print "[uTorrent] Problem sending command " + fnct +  " - " + ex(e)
        return False
    
    if response.status_code == 200:
        return True
    
    print "[uTorrent] Problem sending command " + fnct + ", return code = " + str(response.status_code)
    return False
    
path = str(sys.argv[3])
settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini")    

if settings.uTorrentLabel.lower() == sys.argv[1].lower() or not settings.uTorrentLabel:

    try:
        import requests
        web_ui = settings.uTorrentWebUI
    except:
        web_ui = False

    torrent_hash = sys.argv[6]
    
    # Run a uTorrent action before conversion.
    if web_ui:
        session = requests.Session()
        if session:
            auth,session = _authToken(session, settings.uTorrentHost, settings.uTorrentUsername, settings.uTorrentPassword)
            if auth and settings.uTorrentActionBefore:
                params = {'token': auth, 'action': settings.uTorrentActionBefore, 'hash': torrent_hash}
                _sendRequest(session, settings.uTorrentHost, settings.uTorrentUsername, settings.uTorrentPassword, params, None, "Stop")
       
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

    # Run a uTorrent action after conversion.
    if web_ui: 
        if session and auth and settings.uTorrentActionAfter:
            params = {'token': auth, 'action': settings.uTorrentActionAfter, 'hash': torrent_hash}
            _sendRequest(session, settings.uTorrentHost, settings.uTorrentUsername, settings.uTorrentPassword, params, None, "Remove Data")
            
else:
    print "Incorrect label, ignoring"
