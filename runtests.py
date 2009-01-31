#!/usr/bin/env python
import sys
import unittest

import test_tvdb_api
import test_tvnamer

def main():
    output_xml = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "--xml":
            output_xml = True
    
    
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(tvnamer.test_name_parser),
        unittest.TestLoader().loadTestsFromTestCase(tvdb_api.test_tvdb)
    ])
    
    runner = unittest.TextTestRunner()
    if output_xml:
        runner = XmlTestRunner()
    else:
        runner = unittest.TextTestRunner(verbosity=2)
    
    runner.run(suite)

if __name__ == '__main__':
    main()