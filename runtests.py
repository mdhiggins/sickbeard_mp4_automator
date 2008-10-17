#!/usr/bin/env python
import sys
import unittest

import tvdb_api
import tvnamer

def main():
    output_xml = True; import xmlrunner
    if len(sys.argv) > 1:
        if sys.argv[1] == "--xml":
            import xmlrunner
            output_xml = True
    
    
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(tvnamer.test_name_parser),
        unittest.TestLoader().loadTestsFromTestCase(tvdb_api.test_tvdb)
    ])
    
    runner = unittest.TextTestRunner()
    if output_xml:
        runner = xmlrunner.XmlTestRunner(sys.stdout)
    else:
        runner = unittest.TextTestRunner(verbosity=2)
    
    runner.run(suite)

if __name__ == '__main__':
    main()