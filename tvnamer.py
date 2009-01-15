#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)

"""
tvnamer.py
Automatic TV episode namer.
Uses data from www.thetvdb.com via tvdb_api
"""

__author__ = "dbr/Ben"
__version__ = "0.5"

import os, sys, re
from optparse import OptionParser

from tvdb_api import (tvdb_error, tvdb_shownotfound, tvdb_seasonnotfound,
    tvdb_episodenotfound, tvdb_episodenotfound, tvdb_attributenotfound, tvdb_userabort)
from tvdb_api import Tvdb

config = {}

# The format of the renamed files (with and without episode names)
config['with_ep_name'] = '%(seriesname)s - [%(seasno)02dx%(epno)02d] - %(epname)s.%(ext)s'
config['without_ep_name'] = '%(seriesname)s - [%(seasno)02dx%(epno)02d].%(ext)s'

config['valid_filename_chars'] = """0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@£$%^&*()_+=-[]{}"'.,<>`~? """
config['valid_filename_chars_regex'] = re.escape(config['valid_filename_chars'])

# Regex's to parse filenames with. Must have 3 groups, seriesname, season number
# and episode number. Use (?: optional) non-capturing groups if you need others.
config['name_parse'] = [
    # foo_[s01]_[e01]
    re.compile('''^([%s]+?)[ \._\-]\[[Ss]([0-9]+?)\]_\[[Ee]([0-9]+?)\]?[^\\/]*$'''% (config['valid_filename_chars_regex'])),
    # foo.1x09*
    re.compile('''^([%s]+?)[ \._\-]\[?([0-9]+)x([0-9]+)[^\\/]*$''' % (config['valid_filename_chars_regex'])),
    # foo.s01.e01, foo.s01_e01
    re.compile('''^([%s]+?)[ \._\-][Ss]([0-9]+)[\.\- ]?[Ee]([0-9]+)[^\\/]*$''' % (config['valid_filename_chars_regex'])),
    # foo.103*
    re.compile('''^([%s]+)[ \._\-]([0-9]{1})([0-9]{2})[\._ -][^\\/]*$''' % (config['valid_filename_chars_regex'])),
    # foo.0103*
    re.compile('''^([%s]+)[ \._\-]([0-9]{2})([0-9]{2,3})[\._ -][^\\/]*$''' % (config['valid_filename_chars_regex'])),
]


def findFiles(args, recursive = False):
    """
    Takes a list of files/folders, grabs files inside them. Does not recurse
    more than one level (if a folder is supplied, it will list files within),
    unless recurse is True, in which case it will recursivly find all files.
    """
    allfiles = []
    for cfile in args:
        if os.path.isdir(cfile):
            for sf in os.listdir(cfile):
                newpath = os.path.join(cfile, sf)
                if os.path.isfile(newpath):
                    allfiles.append(newpath)
                else:
                    if recursive:
                        allfiles.extend(
                            findFiles([newpath], recursive = recursive)
                        )
                    #end if recursive
                #end if isfile
            #end for sf
        elif os.path.isfile(cfile):
            allfiles.append(cfile)
        #end if isdir
    #end for cfile
    return allfiles
#end findFiles

def processNames(names, verbose=False):
    """
    Takes list of names, runs them though the config['name_parse'] regexs
    """
    allEps = []
    for f in names:
        filepath, filename = os.path.split( f )
        filename, ext = os.path.splitext( filename )

        # Remove leading . from extension
        ext = ext.replace(".", "", 1)

        for r in config['name_parse']:
            match = r.match(filename)
            if match:
                seriesname, seasno, epno = match.groups()

                #remove ._- characters from name (- removed only if next to end of line)
                seriesname = re.sub("[\._]|\-(?=$)", " ", seriesname).strip()

                seasno, epno = int(seasno), int(epno)

                if verbose:
                    print "*"*20
                    print "File:", filename
                    print "Pattern:", r.pattern
                    print "Seriesname:", seriesname
                    print "Seas:", seasno
                    print "Ep:", epno
                    print "*"*20

                allEps.append({ 'file_seriesname':seriesname,
                                'seasno':seasno,
                                'epno':epno,
                                'filepath':filepath,
                                'filename':filename,
                                'ext':ext
                             })
                break # Matched - to the next file!
        else:
            print "Invalid name: %s" % (f)
        #end for r
    #end for f

    return allEps
#end processNames

def formatName(cfile):
    """
    Takes a file dict and renames files using the configured format
    """
    if cfile['epname']:
        n = config['with_ep_name'] % (cfile)
    else:
        n = config['without_ep_name'] % (cfile)
    #end if epname
    return n
#end formatName

def cleanName(name):
    """
    Cleans the supplied filename for renaming-to
    """
    name = name.encode('ascii', 'ignore') # convert unicode to ASCII

    return ''.join( [c for c in name if c in config['valid_filename_chars']] )
#end cleanName

def renameFile(oldfile, newfile, force=False):
    """
    Renames files, does not overwrite files unless forced
    """
    new_exists = os.access(newfile, os.F_OK)
    if new_exists:
        sys.stderr.write("New filename already exists.. ")
        if force:
            sys.stderr.write("overwriting\n")
            os.rename(oldfile, newfile)
        else:
            sys.stderr.write("skipping\n")
            return False
        #end if force
    else:
        os.rename(oldfile, newfile)
        return True
    #end if new_exists

def processFile(t, opts, cfile):
    try:
        # Ask for episode name from tvdb_api
        epname = t[ cfile['file_seriesname'] ][ cfile['seasno'] ][ cfile['epno'] ]['episodename']
    except tvdb_shownotfound:
        # No such show found.
        # Use the show-name from the files name, and None as the ep name
        sys.stderr.write("! Warning: Show %s not found (in %s)\n" % (
            cfile['file_seriesname'],
            cfile['filepath'] )
        )

        cfile['seriesname'] = cfile['file_seriesname']
        cfile['epname'] = None
    except (tvdb_seasonnotfound, tvdb_episodenotfound, tvdb_attributenotfound):
        # The season, episode or name wasn't found, but the show was.
        # Use the corrected show-name, but no episode name.
        sys.stderr.write("! Warning: Episode name not found for %s (in %s)\n" % (
            cfile['file_seriesname'],
            cfile['filepath'] )
        )

        cfile['seriesname'] = t[ cfile['file_seriesname'] ]['seriesname']
        cfile['epname'] = None
    except tvdb_error, errormsg:
        # Error communicating with thetvdb.com
        sys.stderr.write(
            "! Warning: Error contacting www.thetvdb.com:\n%s\n" % (errormsg)
        )

        cfile['seriesname'] = t[ cfile['file_seriesname'] ]['seriesname']
        cfile['epname'] = None
    except tvdb_userabort, errormsg:
        # User aborted selection (q or ^c)
        print "\n", errormsg
        sys.exit(1)
    else:
        cfile['epname'] = epname
        cfile['seriesname'] = t[ cfile['file_seriesname'] ]['seriesname'] # get the corrected seriesname

    # Format new filename, strip unwanted characters
    newname = formatName(cfile)
    newname = cleanName(newname)

    # Append new filename (with extension) to path
    oldfile = os.path.join(
        cfile['filepath'],
        cfile['filename'] + "." + cfile['ext']
    )
    # Join path to new file name
    newfile = os.path.join(
        cfile['filepath'],
        newname
    )

    # Show new/old filename
    print "#"*20
    print "Old name: %s" % ( cfile['filename'] + "." + cfile['ext'] )
    print "New name: %s" % ( newname )

    # Either always rename, or prompt user
    if opts.always or (not opts.interactive):
        rename_result = renameFile(oldfile, newfile, force=opts.force)
        if rename_result:
            print "..auto-renaming"
        else:
            print "..not renamed"
        #end if rename_result

        return # next filename!
    #end if always

    ans = None
    while ans not in ['y', 'n', 'a', 'q', '']:
        print "Rename?"
        print "([y]/n/a/q)",
        try:
            ans = raw_input().strip()
        except KeyboardInterrupt, errormsg:
            print "\n", errormsg
            sys.exit(1)
        #end try
    #end while

    if len(ans) == 0:
        print "Renaming (default)"
        rename_result = renameFile(oldfile, newfile, force=opts.force)
    elif ans[0] == "a":
        opts.always = True
        rename_result = renameFile(oldfile, newfile, force=opts.force)
    elif ans[0] == "q":
        print "Aborting"
        sys.exit(1)
    elif ans[0] == "y":
        rename_result = renameFile(oldfile, newfile, force=opts.force)
    elif ans[0] == "n":
        print "Skipping"
        return
    else:
        print "Invalid input, skipping"
    #end if ans
    if rename_result:
        print "..renamed"
    else:
        print "..not renamed"
    #end if rename_result
#end processFile

def main():
    parser = OptionParser(usage="%prog [options] <file or directories>")

    parser.add_option(  "-d", "--debug", action="store_true", default=False, dest="debug",
                        help="show debugging info")
    parser.add_option(  "-b", "--batch", action="store_false", dest="interactive",
                        help="selects first search result, requires no human intervention once launched", default=False)
    parser.add_option(  "-i", "--interactive", action="store_true", dest="interactive", default=True,
                        help="interactivly select correct show from search results [default]")
    parser.add_option(  "-r", "--recursive", action="store_true", dest="recursive", default=True,
                        help="recursivly search supplied directories for files to rename")
    parser.add_option(  "-a", "--always", action="store_true", default=False, dest="always",
                        help="always renames files (but still lets user select correct show). Can be changed during runtime with the 'a' prompt-option")
    parser.add_option(  "-f", "--force", action="store_true", default=False, dest="force",
                        help="forces file to be renamed, even if it will overwrite an existing file")
    parser.add_option(  "-t", "--tests", action="store_true", default=False, dest="dotests",
                        help="Run unittests (mostly useful for development)")

    opts, args = parser.parse_args()

    if opts.dotests:
        suite = unittest.TestLoader().loadTestsFromTestCase(test_name_parser)
        unittest.TextTestRunner(verbosity=2).run(suite)
        sys.exit(0)
    #end if dotests

    if len(args) == 0:
        parser.error("No filenames or directories supplied")
    #end if len(args)

    allFiles = findFiles(args, opts.recursive)
    validFiles = processNames(allFiles, verbose = opts.debug)

    if len(validFiles) == 0:
        sys.stderr.write("No valid files found\n")
        sys.exit(2)

    print "#"*20
    print "# Starting tvnamer"
    print "# Processing %d files" % ( len(validFiles) )

    t = Tvdb(debug = opts.debug, interactive = opts.interactive)

    print "# ..got tvdb mirrors"
    print "# Starting to process files"
    print "#"*20

    for cfile in validFiles:
        print "# Processing %(file_seriesname)s (season: %(seasno)d, episode %(epno)d)" % (cfile)
        processFile(t, opts, cfile)
    print "# Done"
#end main

import unittest
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

                proced = processNames(names, self.verbose)
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

if __name__ == "__main__":
    main()
