#!/usr/bin/env python
 
import pycurl
import cStringIO
import urllib
import json
import ConfigParser
import os
import sys
from readSettings import ReadSettings

  
#directory is the path, prob supported in future, status for sanity checking = unnecessary atm
def scan(directory,status=0):

        # Do voodoo with the status, e.g. return earlier.. not sure how..
    
        # Get Settings
        config = ConfigParser.ConfigParser()
        configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcess.ini")
        print "Loading config from", configFilename
        
        if not os.path.isfile(configFilename):
            print "ERROR: You need an autoProcess.ini file - did you rename and edit the .sample?"
            sys.exit(-1)
        
        try:
            fp = open(configFilename, "r")
            config.readfp(fp)
            fp.close()
        except IOError, e:
            print "Could not read configuration file: ", str(e)
            sys.exit(1)

        host = config.get("NzbDrone", "host")
        port = config.get("NzbDrone", "port")
        apikey = config.get("NzbDrone", "api_key")
        try:
            ssl = int(config.get("NzbDrone", "ssl"))
        except (ConfigParser.NoOptionError, ValueError):
            ssl = 0
        
        try:
            web_root = config.get("NzbDrone", "web_root")
        except ConfigParser.NoOptionError:
            web_root = ""
        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"
	#Prepare catching the response
	contents = cStringIO.StringIO()
        #create data structure
        data = {'name': 'downloadedepisodesscan','path': directory }
        postData = json.dumps(data)
        c = pycurl.Curl()
        c.setopt(pycurl.URL, '{0}{1}:{2}{3}/api/command'.format(protocol,host,port,web_root))
        c.setopt(pycurl.HTTPHEADER, ['{0} : {1}'.format('X-Api-Key', apikey)]) 
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.POSTFIELDS, postData)
        try:
            c.perform()
        except pycurl.error, error:
            errno, errstr = error
            print 'An error occurred: ', errstr
            sys.exit(2)

        # Handle the response
	contentasjson = contents.getvalue()
        print contentasjson + "\n==============================\n" #result of API call
        responseCode = c.getinfo(pycurl.HTTP_CODE);
        print 'Response code: ' + str(responseCode);
        isSuccesResponse = responseCode < 400;
        pyobj = json.load(contentasjson)
        # Print information to read on Sabnzbd if went succesfull            
        if (isSuccesResponse):
            print 'Name: ' + str(pyobj['name'])
            print 'StartedOn: ' + str(pyobj['startedOn'])
            print 'StateChangeTime: ' + str(pyobj['stateChangeTime'])
            print 'SendUpdatesToClient: ' + str(pyobj['sendUpdatesToClient'])
            print 'State: ' + str(pyobj['state'])
            print 'SeriesID: ' + str(pyobj['id'])
            # TODO: Tagging of file
            sys.exit(0)                
        else:
            sys.exit(2)
                     


        
