#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)

import sys
import unittest

import test_tvdb_api
import test_tvnamer

def main():
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromModule(test_tvnamer),
        unittest.TestLoader().loadTestsFromModule(test_tvdb_api)
    ])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        return 0
    else:
        return 1

if __name__ == '__main__':
    sys.exit(
        int(main())
    )
