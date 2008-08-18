#!/usr/bin/env python
import unittest

import tvdb_api
import tvnamer

suite = unittest.TestLoader().loadTestsFromTestCase(tvnamer.test_name_parser)
unittest.TextTestRunner(verbosity=2).run(suite)

suite = unittest.TestLoader().loadTestsFromTestCase(tvdb_api.test_tvdb)
unittest.TextTestRunner(verbosity=2).run(suite)
