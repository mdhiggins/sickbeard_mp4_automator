#!/usr/bin/env python
 
import pycurl
import StringIO
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
        username = config.get("NzbDrone", "username")
        password = config.get("NzbDrone", "password")
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
        #create data structure
        data = {'name': 'downloadedepisodesscan','path': directory }
        postData = json.dumps(data)
        c = pycurl.Curl()
        c.setopt(pycurl.URL, '{0}{1}:{2}/{3}/api/command'.format(protocol,host,port,web_root))
        c.setopt(pycurl.HTTPHEADER, ['{0} : {1}'.format('X-Api-Key', apikey)]) 
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.POSTFIELDS, postData)
        #Optional username/password if needed        
        #if username and password:
        #    c.setopt(pycurl.USERPWD, '{0}:{1}'.format(username, password)
        #else:
        #    randomtxt = "without this i had syntax error"          
        #perform the request
        try:
            c.perform()
        except pycurl.error, error:
            errno, errstr = error
            print 'An error occurred: ', errstr

        # Handle the response
        print contents.getvalue() + "\n==============================\n" #result of API call
        responseCode = curl.getinfo(pycurl.HTTP_CODE);
        print 'Response code: ' + str(responseCode);
        isSuccesResponse = responseCode < 400;
        pyobj = json.loads(contents.getvalue())
        print 'Status: ' + str(pyobj['Response']['Status'])
        print 'Code: ' + str(pyobj['Response']['Code'])
        
        # Print information to read on Sabnzbd if went succesfull            
        if (isSuccesResponse):
            print 'Name: ' + str(pyobj['Response']['name'])
            print 'StartedOn: ' + str(pyobj['Response']['startedOn'])
            print 'StateChangeTime: ' + str(pyobj['Response']['stateChangeTime'])
            print 'SendUpdatesToClient: ' + str(pyobj['Response']['sendUpdatesToClient'])
            print 'State: ' + str(pyobj['Response']['state'])
            print 'SeriesID: ' + str(pyobj['Response']['id'])
            #exit succesfull
            sys.exit(0)                
        else:
            print 'Errors: ' + str(pyobj['Response']['Errors']) # Not sure what the correct error response is, did not test it
            sys.exit(1)
                     


        
