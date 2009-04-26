# `tvdb_api` and `tvnamer`

`tvdb_api` is an easy to use interface to [thetvdb.com][tvdb]

`tvnamer` is a utility which uses `tvdb_api`, which renames files from `some.show.s01e03.blah.abc.avi` to `Some Show - [01x03] - The Episode Name.avi` (getting episode names using `tvdb_api`)

## To install

To get `tvnamer` (and `tvdb_api` as a requirement)

    easy_install tvnamer

This installs `tvnamer` as a command-line tool

Or to only get `tvdb_api`

    easy_install tvdb_api

This installs `tvdb_api` as a python module

# `tvnamer`

## Basic usage

From the command line, simply run..

    tvnamer the.file.s01e01.avi

For example:

    $ tvnamer scrubs.s01e01.avi
    ####################
    # Starting tvnamer
    # Processing 1 files
    # ..got tvdb mirrors
    # Starting to process files
    ####################
    # Processing scrubs (season: 1, episode 1)
    TVDB Search Results:
    1 -> Scrubs # http://thetvdb.com/?tab=series&id=76156
    Automatically selecting only result
    ####################
    Old name: scrubs.s01e01.avi
    New name: Scrubs - [01x01] - My First Day.avi
    Rename?
    ([y]/n/a/q)

Entering `y+[return]` (or just enter, to select the default option, denoted by the surrounding `[]`) and the file will be renamed to "Scrubs - [01x01] - My First Day.avi"

You can also rename all multiple files, or an entire directory by doing:

    tvnamer file1.avi file2.avi etc
    
    tvnamer .
    
    tvnamer /path/to/my/folder/

Instead of entering `y` at the prompt, if you enter `a` (always) tvnamer will rename the rest of the files automatically. The suggested use of this is check the first few episodes are named correctly, then use `a` to rename the rest.

Note, tvnamer will only descend one level into directories unless the `-r`/`--recursive` flag is specified, so by default if you have the following directory structure:

    dir1/
        file1.avi
        dir2/
            file2.avi
            file3.avi

..then running `tvnamer dir1/` will only rename `file1.avi` and ignore `dir2/`

If you wish to rename all files (file1, file2 and file3), you would run:

    tvnamer --recursive dir1/

## Advanced usage

There are various flags you can use with `tvnamer`, run..

    tvnamer --help

..to see them, and a short description of each.

The most interesting are most likely `--batch`, `--selectfirst` and `--always`:

`--batch` will not prompt you for anything. It automatically selects the first series search result, and automatically rename all files. Use carefully!

Similarly `--selectfirst` will select the first series the search found, but not automatically rename the episodes. `--always` will let you choose the correct series, but then automatically rename all files.

# `tvdb_api`

## Basic usage

    import tvdb_api
    t = tvdb_api.Tvdb()
    episode = t['My Name Is Earl'][1][3] # get season 1, episode 3 of show
    print episode['episodename'] # Print episode name

## Advanced usage

Most of the documentation is in docstrings. The examples are tested (using doctest) so will always be up to date and working.

See the `Tvdb.__init__` docstring (and others) for various initialisation arguments, including support for non-English searches, custom "Select Series" interfaces and enabling the retrieval of banners and extended actor information.

### Exceptions

There are several exceptions you may catch, these can import from `tvdb_api`:

- `tvdb_error` - this is raised when there is an error communicating with [www.thetvdb.com][tvdb] (a network error most commonly)
- tvdb_userabort - raised when a user aborts the Select Series dialog (by `ctrl+c`, or entering `q`)
- `tvdb_shownotfound` - raised when `t['show name']` cannot find anything
- `tvdb_seasonnotfound` - raised when the requested series (`t['show name][99]`) does not exist
- `tvdb_episodenotfound` - raised when the requested episode (`t['show name][1][99]`) does not exist.
- `tvdb_attributenotfound` - raised when the requested attribute is not found (`t['show name']['an attribute']`, `t['show name'][1]['an attribute']`, or ``t['show name'][1][1]['an attribute']``)

### Series data

All data exposed by [thetvdb.com][tvdb] is accessible via the `Show` class. A Show is retrieved by doing..

    >>> import tvdb_api
    >>> t = tvdb_api.Tvdb()
    >>> show = t['scrubs']
    >>> type(show)
    <class 'tvdb_api.Show'>

For example, to find out what network Scrubs is aired:

    >>> t['scrubs']['network']
    u'NBC|ABC'

The data is stored in an attribute named `data`, within the Show instance:

    >>> t['scrubs'].data.keys()
    ['networkid', 'rating', 'airs_dayofweek', 'contentrating', 'seriesname', 'id', 'airs_time', 'network', 'fanart', 'lastupdated', 'actors', 'overview', 'status', 'added', 'poster', 'imdb_id', 'genre', 'banner', 'seriesid', 'language', 'zap2it_id', 'addedby', 'firstaired', 'runtime']

Although each element is also accessible via `t['scrubs']` for ease-of-use:

    >>> t['scrubs']['rating']
    u'9.1'

This is the recommended way of retrieving "one-off" data (for example, if you are only interested in "seriesname"). If you wish to iterate over all data, or check if a particular show has a key, use the `data` attribute

### Banners and actors

Since banners and actors are separate XML, retrieving them by default is unnecessary. If you wish to retrieve banners (and other fanart), use the banners Tvdb initialisation argument:

    >>> t = Tvdb(banners = True)

Then access the data using a `Show`'s `_banner` key:

    >>> t['scrubs']['_banners'].keys()
    ['fanart', 'poster', 'series', 'season']

The banner data structure will be improved in future versions.

Extended actor data is accessible similarly:

    >>> t = Tvdb(actors = True)
    >>> actors = t['scrubs']['_actors']
    >>> actors[0]
    >>> actors[0]
    <Actor "Zach Braff">
    >>> actors[0].keys()
    ['image', 'sortorder', 'role', 'id', 'name']
    >>> actors[0]['role']
    u'Dr. John Michael "J.D." Dorian'

Remember a simple list of actors is accessible via the default Show data:

    >>> t['scrubs']['actors']
    u'|Zach Braff|Donald Faison|Sarah Chalke|Christa Miller Lawrence|Aloma Wright|Robert Maschio|Sam Lloyd|Neil Flynn|Ken Jenkins|Judy Reyes|John C. McGinley|'

[tvdb]: www.thetvdb.com