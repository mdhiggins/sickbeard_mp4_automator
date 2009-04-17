#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)

"""Unittests for tvnamer
"""

import sys
import unittest

sys.path.append("..")

import tvnamer

class test_name_parser(unittest.TestCase):
    def setUp(self):
        """
        Define name formats to test.
        %(seriesname)s becomes the seriesname,
        %(seasno)s becomes the season number,
        %(epno)s becomes the episode number.

        The verbose setting currently shows which
        regex matches each filename, and the values
        it found in each of the three groups.
        """
        # Shows verbose regex matching information
        self.verbose = False

        #scene naming standards: http://tvunderground.org.ru/forum/index.php?showtopic=8488
        self.name_formats = [
            '%(seriesname)s.s%(seasno)de%(epno)d.dsr.nf.avi',                 #seriesname.s01e02.dsr.nf.avi
            '%(seriesname)s.S%(seasno)dE%(epno)d.PROPER.dsr.nf.avi',          #seriesname.S01E02.PROPER.dsr.nf.avi
            '%(seriesname)s.s%(seasno)d.e%(epno)d.avi',                       #seriesname.s01.e02.avi
            '%(seriesname)s-s%(seasno)de%(epno)d.avi',                        #seriesname-s01e02.avi
            '%(seriesname)s-s%(seasno)de%(epno)d.the.wrong.ep.name.avi',      #seriesname-s01e02.the.wrong.ep.name.avi
            '%(seriesname)s - [%(seasno)dx%(epno)d].avi',                     #seriesname - [01x02].avi
            '%(seriesname)s - [%(seasno)dx0%(epno)d].avi',                    #seriesname - [01x002].avi
            '%(seriesname)s-[%(seasno)dx%(epno)d].avi',                       #seriesname-[01x02].avi
            '%(seriesname)s [%(seasno)dx%(epno)d].avi',                       #seriesname [01x02].avi
            '%(seriesname)s [%(seasno)dx%(epno)d] the wrong ep name.avi',     #seriesname [01x02] epname.avi
            '%(seriesname)s [%(seasno)dx%(epno)d] - the wrong ep name.avi',   #seriesname [01x02] - the wrong ep name.avi
            '%(seriesname)s - [%(seasno)dx%(epno)d] - the wrong ep name.avi', #seriesname - [01x02] - the wrong ep name.avi
            '%(seriesname)s.%(seasno)dx%(epno)d.The_Wrong_ep_name.avi',       #seriesname.01x02.epname.avi
            '%(seriesname)s.%(seasno)d%(epno)02d.The Wrong_ep.names.avi',     #seriesname.102.epname.avi
            '%(seriesname)s_s%(seasno)de%(epno)d_The_Wrong_ep_na-me.avi',     #seriesname_s1e02_epname.avi
            '%(seriesname)s - s%(seasno)de%(epno)d - dsr.nf.avi'              #seriesname - s01e02 - dsr.nf.avi
            '%(seriesname)s - s%(seasno)de%(epno)d - the wrong ep name.avi'   #seriesname - s01e02 - the wrong ep name.avi
            '%(seriesname)s - s%(seasno)de%(epno)d - the wrong ep name.avi'   #seriesname - s01e02 - the_wrong_ep_name!.avi
        ]

    def test_name_parser_basic(self):
        """Tests most basic filename (simple seriesname)
        """
        name_data = {'seriesname':'series name'}

        self._run_test(name_data)
    #end test_name_parser

    def test_name_parser_showdashname(self):
        """Tests with dash in seriesname
        """
        name_data = {'seriesname':'S-how name'}

        self._run_test(name_data)
    #end test_name_parser_showdashname

    def test_name_parser_shownumeric(self):
        """Tests with numeric show name
        """
        name_data = {'seriesname':'123'}

        self._run_test(name_data)
    #end test_name_parser_shownumeric

    def test_name_parser_shownumericspaces(self):
        """Tests with numeric show name, with spaces
        """
        name_data = {'seriesname':'123 2008'}

        self._run_test(name_data)
    #end test_name_parser_shownumeric

    def test_name_parser_exclaim(self):
        """Tests parsing show with explaimation mark
        """
        name_data = {'seriesname':'Show name!'}

        self._run_test(name_data)
    #end test_name_parser_exclaim
    
    def test_name_parser_unicode(self):
        """Tests parsing show containing unicode characters"""
        name_data = {'seriesname':u'T\xecnh Ng\u01b0\u1eddi Hi\u1ec7n \u0110\u1ea1i'.encode("utf-8")}
        
        self._run_test(name_data)
    #end test_name_parser_unicode

    def _run_test(self, name_data):
        """
        Runs the tests and checks if the parsed values have
        the correct seriesname/season number/episode number.
        Runs from season 0 ep 0 to season 10, ep 10.
        """
        for seas in xrange(1, 11):
            for ep in xrange(1, 11):
                name_data['seasno'] = seas
                name_data['epno'] = ep

                names = [x % name_data for x in self.name_formats]

                proced = tvnamer.processNames(names, self.verbose)
                self.assertEquals(len(names), len(proced))

                for c in proced:
                    try:
                        self.assertEquals( c['epno'], name_data['epno'])
                        self.assertEquals( c['seasno'], name_data['seasno'] )
                        self.assertEquals( c['file_seriesname'], name_data['seriesname'] )
                    except AssertionError, errormsg:
                        # Show output of regex match in traceback (instead of "0 != 10")
                        new_errormsg = str(c) + "\n" + str(errormsg)
                        raise AssertionError, new_errormsg
                #end for c in proced
            #end for ep
        #end for seas
    #end run_test
#end test_name_parser

if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity = 2)
    unittest.main(testRunner = runner)
