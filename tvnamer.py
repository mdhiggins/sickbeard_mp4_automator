#!/usr/bin/env python
#encoding:utf-8

#
# TVNamer.py
# Automatic TV episode namer.
# Uses data from www.thetvdb.com via tvdb_api
#
__author__ = "dbr/Ben"
__version__ = "0.1"

import os,sys,re
from optparse import OptionParser
from tvdb_api import tvdb

config={}

config['with_ep_name'] = '%(showname)s - [%(seasno)02dx%(epno)02d] - %(epname)s.%(ext)s'
config['without_ep_name'] = '%(showname)s - [%(seasno)02dx%(epno)02d].%(ext)s'

config['name_parse'] = [
    # show name - [01x23] - blah
    re.compile('''
    ^(
        [\w\. ]* # show name
    )
    (?: \- )? # -
    [\[ ]{1,2}           #(?=\[)? #.*?
    .*?
        (\d+)x(\d+)
    .*?
    (?:\])?
    .*?
    $
    ''', re.IGNORECASE|re.VERBOSE),
    
    # show.name.s01e02
    re.compile('''
    ^(
        [\w\. ]*
    )
    #[-. ]{1}
    (?: \- |\.|\-)?
    s(\d+)
        (?:[\.\-]{1})?
    e(\d+)
    (?:\D|$)
    ''', re.IGNORECASE|re.VERBOSE ),
    
    re.compile('''
    ^(
        [\w\. ]*
    )
    (?= \- |\.)?
    .*?
    (?=\d+)x(\d+)(\D|$)
    ''', re.IGNORECASE|re.VERBOSE ),
    
    re.compile('''
    ^(
        [\w\. ]*
    )
    (?= \- )?
    \D+
    (\d+?)(\d{2})
    .*?
    (?=\D|$)''', re.IGNORECASE|re.VERBOSE ),
]

config['valid_filename_chars'] = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@£$%^&*()_+=-[]{}\"'.,<>`~? "

def findFiles(args):
    allfiles=[]
    for x in args:
        if os.path.isdir(x):
            for sf in os.listdir(x):
                newpath = os.path.join(x,sf)
                if os.path.isfile(newpath):
                    allfiles.append(newpath)
                #end if isfile
            #end for sf
        elif os.path.isfile(x):
            allfiles.append(x)
        #end if isdir
    #end for x
    return allfiles
#end findFiles

def processNames(names):
    allEps=[]
    for f in names:
        filepath,filename = os.path.split( f )
        filename,ext = os.path.splitext( filename )
        for r in config['name_parse']:
            match = r.match(filename)
            if match:
                showname,seasno,epno = match.groups()
                showname = showname.replace("."," ").strip()
                seasno,epno = int(seasno), int(epno)
                allEps.append({ 'file_showname':showname,
                                'seasno':seasno,
                                'epno':epno,
                                'filepath':filepath,
                                'filename':filename,
                                'ext':ext
                             })
                break
        else:
            print "Invalid name %s"%(f)
        #end for r
    #end for f
    
    return allEps
#end processNames

def formatName(cfile):
    orig_ext = cfile['ext']
    cfile['ext'] = cfile['ext'].replace(".","",1)
    if cfile['epname']:
        n = config['with_ep_name'] % (cfile)
    else:
        n = config['without_ep_name'] % (cfile)
    #end if epname
    cfile['ext'] = orig_ext 
    return n
#end formatName

def cleanName(name):
    name = name.encode('ascii','ignore') # convert unicode to ASCII
    
    return ''.join( [c for c in name if c in config['valid_filename_chars']] )
        

def renameFile(oldfile,newfile,force=False):
    new_exists = os.access(newfile,os.F_OK)
    if new_exists:
        sys.stderr.write("New filename already exists.. ")
        if force:
            sys.stderr.write("overwriting\n")
            os.rename(oldfile,newfile)
        else:
            sys.stderr.write("skipping\n")
            return False
        #end if force
    else:
        os.rename(oldfile,newfile)
        return True
    #end if new_exists
    

def main():
    parser = OptionParser(usage="%prog [options] <file or directories>")

    parser.add_option(  "-d","--debug",action="store_true",default=False,dest="debug",
                        help="show debugging info")
    parser.add_option(  "-b","--batch",action="store_false",dest="interactive",
                        help="selects first search result, requires no human intervention once launched",default=False)
    parser.add_option(  "-i","--interactive",action="store_true",dest="interactive",default=True,
                        help="interactivly select correct show from search results [default]")
    parser.add_option(  "-a","--always",action="store_true",default=False,dest="always",
                        help="always renames files (but still lets user select correct show). Can be changed during runtime with the 'a' prompt-option")
    parser.add_option(  "-f","--force",action="store_true",default=False,dest="force",
                        help="forces file to be renamed, even if it will overwrite an existing file")
    parser.add_option(  "-t","--tests",action="store_true",default=False,dest="dotests",
                        help="Run unittests (mostly useful for development)")
    
    opts,args = parser.parse_args()

    if len(args) == 0:
        parser.error("No filenames or directories supplied")
    #end if len(args)
    
    allFiles = findFiles(args)
    validFiles = processNames(allFiles)
    
    if len(validFiles) == 0:
        sys.stderr.write("No valid files found\n")
        sys.exit(1)
    
    print "#"*20
    print "# Starting tvnamer"
    print "# Processing %d files" % ( len(validFiles) )
    
    t = tvdb(debug = opts.debug, interactive = opts.interactive)
    
    print "# ..got tvdb mirrors"
    print "# Starting to process files"
    
    for cfile in validFiles:
        
        # Ask for episode name from tvdb_api
        try:
            epname = t[ cfile['file_showname'] ][ cfile['seasno'] ][ cfile['epno'] ]['name']
        except tvdb_shownotfound:
            # No such show
            epname = None
            showname = None
        finally:
            showname = t[ cfile['file_showname'] ]['showname'] # get the corrected showname
        
        # Either use the found episode name, warn if not found
        if epname:
            cfile['epname'] = epname
        else:
            cfile['epname'] = None
            sys.stderr.write("! Episode name not found for %s\n" % ( cfile ) )
        #end if epname
        
        if showname:
            cfile['showname'] = showname
        else:
            cfile['showname'] = cfile['file_showname'] # no corrected showname found, use one from filename
        
        # Format new filename, strip unwanted characters
        newname = formatName( cfile )
        newname = cleanName(newname)
        
        # Append new filename (with extension) to path
        oldfile = os.path.join(
            cfile['filepath'], 
            cfile['filename'] + cfile['ext']
        )
        # Join path to new file name
        newfile = os.path.join(
            cfile['filepath'], 
            newname
        )
        
        # Show new/old filename
        print "#"*20
        print "Old name: %s" % ( cfile['filename'] + cfile['ext'] )
        print "New name: %s" % ( newname )
        
        # Either always rename, or prompt user
        if opts.always or not opts.interactive:
            rename_result = renameFile(oldfile,newname,force=opts.force)
            if rename_result:
                print "..auto-renaming"
            else:
                print "..not renamed"
            continue # next filename!
        #end if always
        
        print "Rename?"
        print "(y/n/a/q)",
        ans=raw_input()
        if ans[0] == "a":
            always=True
            rename_result = renameFile(oldfile,newname,force=opts.force)
        elif ans[0] == "q":
            print "Aborting"
            break
        elif ans[0] == "y":
            rename_result = renameFile(oldfile,newname,force=opts.force)
        elif ans[0] == "n":
            print "Skipping"
            continue
        #end if ans
        if rename_result:
            print "..renamed"
        else:
            print "..not renamed"
        #end if rename_result
    #end for cfile
#end main

import unittest
class test_tvnamer(unittest.TestCase):
    def test_name_parser(self):
        names = [
            'show.name.s01e21.dsr.nf.avi',
            'show.name.s01.e21.avi',
            'show.name-s01e21.avi',
            'show.name-s01e21.the.wrong.ep.name.avi',
            'show.name.s01e21.dsr.nf.avi',
            'show name - [01x21].avi',
            'show name - [1x21].avi',
            'show name - [1x21].avi',
            'show name - [01x021].avi',
            'show name-[01x21].avi',
            'show name [01x21].avi',
            'show name [01x21] - the wrong ep name.avi',
            'show name [01x21] the wrong ep name.avi',
        ]
        proced = processNames(names)
        self.assertEquals( len(names), len(proced) )
        for c in proced:
            self.assertEquals( c['epno'], 21)
            self.assertEquals( c['seasno'], 1 )
            self.assertEquals( c['file_showname'], 'show name' )
    #end test_01_21
    
    def test_tvdb(self):
        import tvdb_api
        t=tvdb_api.tvdb()
        self.assertEquals(t['scrubs'][1][4]['name'], 'My Old Lady')
        self.assertEquals(t['sCruBs']['showname'], 'Scrubs')
        
        self.assertEquals(t['24'][2][20]['name'], 'Day 2: 3:00 A.M.-4:00 A.M.')
        self.assertEquals(t['24']['showname'], '24')
        self.assertRaises(tvdb_api.tvdb_shownotfound,t['the fake show thingy'])
    #end test_tvdb
    
#end test_nameregexes

if __name__ == "__main__":
    unittest.main()
    main()
