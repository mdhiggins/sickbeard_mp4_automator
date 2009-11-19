#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)

"""Functional tests for tvnamer
"""

import os
import sys
import unittest
import tempfile
from subprocess import Popen, PIPE

def make_temp_dir():
    return tempfile.mkdtemp()

def make_dummy_files(files, location):
    for f in files:
        floc = os.path.join(location, f)
        open(floc, "w").close()

def get_tvnamer_path():
    cur_location, _ = os.path.split(
        os.path.abspath(sys.path[0])
    )
    for cdir in [".", ".."]:
        tvnamer_location = os.path.abspath(
            os.path.join(cur_location, cdir, "tvnamer.py")
        )
        if os.path.isfile(tvnamer_location):
            return tvnamer_location
        else:
            print tvnamer_location
    else:
        raise IOError("tvnamer could not be found in . or ..")

def tvnamerifiy(location):
    log = []
    
    tvn = get_tvnamer_path()
    for f in os.listdir(location):
        fullpath = os.path.join(location, f)
        proc = Popen(
            [sys.executable, tvn, "-b", fullpath],
            stdout = PIPE
        )
        stdout, stderr = proc.communicate()
        log.append({'filename':f, 'stdout': stdout, 'stderr':stderr})
    
    return log

def verify_naming(files, location):
    dirlist = os.listdir(location)
    pass_log = []
    error_log = []
    for cur in files:
        if cur['expected'] in dirlist:
            pass_log.append(cur)
        else:
            error_log.append(cur)
    
    return (pass_log, error_log)

def clear_temp_dir(location):
    print "Clearing %s" % location
    for f in os.listdir(location):
        fullpath = os.path.join(location, f)
        os.unlink(fullpath)

class functional_tests(unittest.TestCase):
    def test_functional(self):
        """Tests tvnamer functions correctly in batch mode
        """
        tests = [
            {'in':'scrubs.s01e01.hdtv.fake.avi',
            'expected':'Scrubs - [01x01] - My First Day.avi'},
            {'in':'my.name.is.earl.s01e01.fake.avi',
            'expected':'My Name Is Earl - [01x01] - Pilot.avi'},
            {'in':'a.fake.show.s12e24.fake.avi',
            'expected':'a fake show - [12x24].avi'}
        ]
        tmp = make_temp_dir()
        make_dummy_files(
            [x['in'] for x in tests],
            tmp
        )
        log = tvnamerifiy(tmp)
    
        (pass_log, error_log) = verify_naming(tests, tmp)
    
        #if len(pass_log) > 0:
        #    print "Passed:"
        #    for cur in pass_log:
        #        print "OK: %(in)s -> %(expected)s" % cur
    
        if len(error_log) > 0:
            print "Ended up with files:"
            print os.listdir(tmp)
            print "*" * 60
            print "Errors:"
            for cur in error_log:
                print "ERROR: %(in)s -> %(expected)s" % cur
    
        print
        print "*" * 60
        clear_temp_dir(tmp)
        self.assertTrue(len(pass_log) > 0)
        self.assertTrue(len(error_log) == 0)

if __name__ == '__main__':
    unittest.main()
