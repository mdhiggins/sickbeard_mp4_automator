#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)

"""Unittests for tvdb_api
"""

import sys
import unittest

sys.path.append("..")

import tvdb_api
from tvdb_exceptions import (tvdb_error, tvdb_userabort, tvdb_shownotfound,
    tvdb_seasonnotfound, tvdb_episodenotfound, tvdb_attributenotfound)

class test_tvdb(unittest.TestCase):
    # Used to store the cached instance of Tvdb()
    t = None
    
    def setUp(self):
        if self.t is None:
            self.__class__.t = tvdb_api.Tvdb(cache = False, banners = False)
     
    def test_different_case(self):
        """Checks the auto-correction of show names is working.
        It should correct the weirdly capitalised 'sCruBs' to 'Scrubs'
        """
        self.assertEquals(self.t['scrubs'][1][4]['episodename'], 'My Old Lady')
        self.assertEquals(self.t['sCruBs']['seriesname'], 'Scrubs')

    def test_spaces(self):
        """Checks shownames with spaces
        """
        self.assertEquals(self.t['My Name Is Earl']['seriesname'], 'My Name Is Earl')
        self.assertEquals(self.t['My Name Is Earl'][1][4]['episodename'], 'Faked His Own Death')

    def test_numeric(self):
        """Checks numeric show names
        """
        self.assertEquals(self.t['24'][2][20]['episodename'], 'Day 2: 3:00 A.M.-4:00 A.M.')
        self.assertEquals(self.t['24']['seriesname'], '24')

    def test_seasonnotfound(self):
        """Checks exception is thrown when season doesn't exist.
        """
        self.assertRaises(tvdb_seasonnotfound, lambda:self.t['CNNNN'][10][1])

    def test_shownotfound(self):
        """Checks exception is thrown when episode doesn't exist.
        """
        self.assertRaises(tvdb_shownotfound, lambda:self.t['the fake show thingy'])
    
    def test_episodenotfound(self):
        """Checks exception is raised for non-existant episode
        """
        self.assertRaises(tvdb_episodenotfound, lambda:self.t['Scrubs'][1][30])

    def test_attributenamenotfound(self):
        """Checks exception is thrown for if an attribute isn't found.
        """
        self.assertRaises(tvdb_attributenotfound, lambda:self.t['CNNNN'][1][6]['afakeattributething'])
        self.assertRaises(tvdb_attributenotfound, lambda:self.t['CNNNN']['afakeattributething'])

    def test_search_len(self):
        """There should be only one result matching
        """
        self.assertEquals(len(self.t['My Name Is Earl'].search('Faked His Own Death')), 1)

    def test_search_checkname(self):
        """Checks you can get the episode name of a search result
        """
        self.assertEquals(self.t['Scrubs'].search('my first')[0]['episodename'], 'My First Day')
        self.assertEquals(self.t['My Name Is Earl'].search('Faked His Own Death')[0]['episodename'], 'Faked His Own Death')
    
    def test_search_multiresults(self):
        """Checks search can return multiple results
        """
        self.assertEquals(len(self.t['Scrubs'].search('my first')) >= 3, True)

    def test_get_episode_overview(self):
        """Checks episode overview is retrived correctly.
        """
        self.assertEquals(
            self.t['Battlestar Galactica (2003)'][1][6]['overview'].startswith(
                'When a new copy of Doral, a Cylon who had been previously'),
            True
        )
    
    def test_search_no_params_error(self):
        """Checks not supplying search info rasies TypeError"""
        self.assertRaises(
            TypeError,
            lambda: self.t['Scrubs'].search()
        )
    
    def test_show_iter(self):
        """Iterating over a show returns each seasons
        """
        self.assertEquals(
            len(
                [season for season in self.t['Life on Mars']]
            ),
            2
        )
    
    def test_season_iter(self):
        """Iterating over a show returns episodes
        """
        self.assertEquals(
            len(
                [episode for episode in self.t['Life on Mars'][1]]
            ),
            8
        )
    
    def test_episode_data(self):
        """Check the firstaired value is retrived
        """
        self.assertEquals(
            self.t['lost']['firstaired'],
            '2004-09-22'
        )

    def test_repr_show(self):
        """Check repr() of Season
        """
        self.assertEquals(
            repr(self.t['CNNNN']),
            "<Show Chaser Non-Stop News Network (CNNNN) (containing 2 seasons)>"
        )
    def test_repr_season(self):
        """Check repr() of Season
        """
        self.assertEquals(
            repr(self.t['CNNNN'][1]),
            "<Season instance (containing 9 episodes)>"
        )
    def test_repr_episode(self):
        """Check repr() of Episode
        """
        self.assertEquals(
            repr(self.t['CNNNN'][1][1]),
            "<Episode 01x01 - September 19, 2002 (20:30 - 21:00)>"
        )
    
    def test_have_banners(self):
        """Check banners at least one banner is found
        """
        self.assertEquals(
            len(self.t['scrubs']['_banners']) > 0,
            True
        )
    
    def test_banner_url(self):
        """Checks banner URLs start with http://
        """
        orig_banners_enabled = self.t.config['banners_enabled']
        self.t.config['banners_enabled'] = True
        for banner_type, banner_data in self.t['scrubs']['_banners'].items():
            for res, res_data in banner_data.items():
                for bid, banner_info in res_data.items():
                    self.assertEquals(
                        banner_info['_bannerpath'].startswith("http://"),
                        True
                    )
        self.t.config['banners_enabled'] = orig_banners_enabled
    
    def test_doctest(self):
        """Check docstring examples works"""
        import doctest
        doctest.testmod(tvdb_api)
#end test_tvdb

if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity = 2)
    unittest.main(testRunner = runner)
