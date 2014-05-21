Sick Beard/Couch Potato MP4 automation script.
==============

**Automatically converts mkv files downloaded by Sick Beard to mp4 files, and tags them with the appropriate metadata from theTVDB. Works as an extra_script, integrated with SAB, as well as a manual post-processing script.**

**Works with Couch Potato as well, tagging with the appropriate metadata from IMDb. Additional SAB scripts provided for conveinence. uTorrent BETA support added as well**

- Requires Python 2.7 *(Does NOT work with Python 3)*
- Requires FFMPEG and FFPROBE
- Works on Windows, OSX, and Linux (Linux users make sure you're using a build of FFMPEG with the non open-source codecs, see here: https://ffmpeg.org/trac/ffmpeg/wiki/UbuntuCompilationGuide)

Default Settings
--------------
1. Video - H264
2. Audio - AAC 2.0 with additional AC3 track when source has >2 channels (ex 5.1)
3. Subtitles - mov_text

General Installation Instructions
--------------
1. Rename autoProcess.ini.sample to autoProcess.ini
2. Set the MP4 variables to your desired output
    - `ffmpeg` = Path to FFMPEG.exe
    - `ffprobe` = Path to FFPROBE.exe
    - `output_directory` = you may specify an alternate output directory. Leave blank to use the same directory that the source file is in. All processing will be done in this location. (Do not use for 'Automatically Add to iTunes' folder, iTunes will add prematurely, use `move_to`)
    - `copy_to` = you may specify additional directories for the final product to be replicated to. This will be the last step performed so the file copied will be fully processed. Directories may be separated with a `|` character
    - `move_to` = you may specify one final directory to move the completed file. (Use this option for the 'Automatically Add to iTunes' folder)
    - `output_extension` = mp4/m4v (must be one of these 2)
    - `output_format` = mp4/mov (must be one of these 2, mov provides better compatability with iTunes/Apple, mp4 works better with other mobile devices)
    - `delete_original` = True/False
    - `relocate_moov` = True/False - relocates the MOOV atom to the beginning of the file for better streaming
    - `ios-audio` = creates a 2nd copy of an audio stream that will be iOS compatible (AAC Stereo) if the normal output will not be. If a stereo source stream is detected with this option enabled, an AAC stereo stream will be the only one produced (essentially overriding the codec option) to avoid multiple stereo audio stream copies in different codecs.
    - `video-codec` = set your desired video codecs. May specificy multiple comma separated values (ex: h264, x264). The first value specified will be the default conversion choice when an undesired codec is encountered; any codecs specified here will be remuxed/copied rather than converted. 
    - `audio-codec` = set your desired audio codecs. May specificy multiple comma separated values (ex: ac3, aac). The first value specified will be the default conversion choice when an undesired codec is encountered; any codecs specified here will be remuxed/copied rather than converted. 
    - `audio-language` = 3 letter language code for audio streams you wish to copy. Leave blank to copy all. Separate multiple audio streams with commas (ex: eng,spa)
    - `audio-default-language` = If an audio stream with an unidentified/untagged language is detected, you can default that language tag to whatever this value is (ex: eng). This is useful for many single-audio releases which don't bother to tag the audio stream as anything
    - `subtitle-language` = same as audio-language but for subtitles
    - `subtitle-language-default` = same as audio-language-default but for subtitles
    - `convert-mp4` = forces the script to reprocess and convert mp4 files as though they were mkvs. Good if you have old mp4's that you want to match your current codec configuration.
    - `fullpathguess` = True/False - When manually processing a file, enable to guess metadata using the full path versus just the file name. (Files shows placed in a 'Movies' folder will be recognized as movies, not as TV shows for example.)
    - `tagfile` = True/False - Enable or disable tagging file with appropriate metadata after encoding.
    - `download-artwork` = True/False - Enabled downloading and embeddeding of Season or Movie posters and embeddeding of that image into the mp4 as the cover image.
    - `download-subs` = True/False - When enabled the script will attempt to download subtitles of your specified languages automatically using subliminal and merge them into the final mp4 file. 
    - `embed-subs` = True/False - Enabled by default. Embeds subtitles in the resulting MP4 file that are found embedded in the source file as well as external SRT files. Disabling embed-subs will cause the script to extract any subtitles that meet your language criteria into external SRT files. The script will also attempt to download SRT files if possible and this feature is enabled.
    **YOU MUST INSTALL SUBLIMINAL AND ITS DEPENDENCIES FOR THIS TO WORK.** You must go into the `setup\subliminal` directory included in this script and run `setup.py install` to add support for fetching of subtitles. The version included with this script is modified from the stock version of subliminal, so you must install the included version.
    - `sub-providers` = Comma separated values for potential subtitle providers. Must specify at least 1 provider to enable `download-subs`. Providers include `podnapisi` `thesubdb` `opensubtitles` `tvsubtitles` `addic7ed` 

Sick Beard Installation Instructions
--------------
1. Open Sickbeard's config.ini in Sick Beard and set your "extra_scripts" value in the general section to the full path to "python postConversion.py" using double backslashes (C:\\Python27\\python C:\\Scripts\\postConversion.py). Make sure this is done while Sick Beard is not running or it will be reverted. And make sure python is registered as an environment variable/PATH. With the latest version of Sickbeard you must specify the absolute path to the python executable, otherwise you'll get an "Error 2"
2. Set the SickBeard variables in autoProcess.ini:
    - `host` = Sick Beard host address (localhost)
    - `port` = Sick Beard port (8081)
    - `ssl` = 0/1
    - `api_key` = Set this to your Sick Beard API key (options -> general, enable API in Sick Beard to get this key)
3. **OPTIONAL** - If you're using SAB, set your post processing script to sabToSickBeardWithConverter.py - this is not completely needed but gives the added benefit of doing the conversion from mkv to mp4 before Sick Beard sees the file in whatever folder you choose to download things to. It saves having to put in all the API information as well, and prevents the one additional refresh needed normally to have Sick Beard see the properly converted file. That being said the postConversion script can handle everything on its own, so this step is just for the added benefits listed.

NzbDrone Support (Beta, Tagging Not Supported)
--------------
1. Set your NzbDrone settings to the autoProcess.ini file
    - `host` = NzbDrone host address (localhost)    #Settings/General/Start-Up
    - `port` = NzbDrone port (8989)                 #Settings/General/Start-Up
    - `ssl` = 1 if enabled, 0 if not                #Settings/General/Security
    - `api_key` = NzbDrone API Key (required)       #Settings/General/Security
    - `web_root` = URL base empty or e.g. /nzbdrone #Settings/General/Start-Up
2. Browse to the [Download Client] tab and enable advanced settings [Show].
3. Set the {Drone Factory Interval} to 0 to disable it. (Sabnzbd will trigger a specific path re-scan, allowing the mp4 conversion to be completed before NzbDrone starts moving stuff around).
4. Add a category for NzbDrone downloads ( e.g. nzbdrone) and set the script to nzbToNzbDroneMp4.py

Couch Potato Support
--------------
1. Set your Couch Potato settings to the autoProcess.ini file
    - `host` = Couch Potato host address (localhost)
    - `port` = Couch Potato port (5050)
    - `ssl` = 1 if enabled, 0 if not
    - `api_key` = Couch Potato API Key (required)
    - `username` = your Couch Potato username
    - `password` = your Couch Potato password
2. Copy the PostProcess directory from the setup folder included with this script to the Couch Potato custom_plugins directory. You can find this directory within your Couch Potato setup by opening Couch Potato and navigating to the About page, where the installation directory is displayed. Copy the PostProcess folder (the whole folder, not just the contents) to Couch Potato and restart Couch Potato. You should see in the logs that it was loaded. Also you'll need to open up the main.py file and set the path variable to the directory where your CPProcess.py script resides, which by default points to C:\\Scripts\\. Use double backslashes. If you make any changes here make sure to delete the `.pyc` files.
3. Disable automatic checking of the renamer folder, the script will automatically notify Couch Potato when it is complete to check for new videos to be renamed and relocated. Leaving this on may cause conflicts and CouchPotato may try to relocate/rename the file before processing is completed.
    - Set `Run Every` to `0` 
    - Set `Force Every` to `0`
    - **WARNING** On Windows there is currently a bug that prevents the script from triggering on its own (will be fixed in the next CP build) so you must set a time interval for CouchPotato to scan the folder, so set Run Every to some non-zero number (>10 preferred)
4. **OPTIONAL** Point your Couch Potato videos that are sent to SAB to nzbToCouchPotatoMP4.py for post processing; this will convert them before they are passed to Couch Potato. Without this step video files will be converted after being processed by CouchPotato.

uTorrent Support (BETA)
--------------
- `uTorrentToSickbeardwithConverter.py` is the file you'll be using here. This script will allow post processing of torrent files with conversion and will forward the converted files to Sickbeard for final post processing.
- Currently the script will not touch the actual download but will instead make copies (the script will obey settings regarding output directory, copyto, moveto etc) and process those copies, so you can continue to seed your torrents.
- uTorrent must be set up with the following post command options: ```#Args: %L %T %D %K %F```
- Picture: http://i.imgur.com/7eADkCI.png


Manual Script Usage
--------------
To run the script manually, simply run the manual.py file and follow the prompts it presents.
If you wish to run it via the command line (good for batch operations) follow this format:

```
Help output
manual.py -h
usage: manual.py [-h] [-i INPUT] [-a] [-tv TVDBID] [-s SEASON] [-e EPISODE]
                 [-imdb IMDBID] [-tmdb TMDBID] [-nm] [-nc] [-nd]

Manual conversion and tagging script for sickbeard_mp4_automator

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        The source that will be converted. May be a file or a
                        directory
  -a, --auto            Enable auto mode, the script will not prompt you for
                        any further input, good for batch files. It will guess
                        the metadata using guessit
  -tv TVDBID, --tvdbid TVDBID
                        Set the TVDB ID for a tv show
  -s SEASON, --season SEASON
                        Specifiy the season number
  -e EPISODE, --episode EPISODE
                        Specify the episode number
  -imdb IMDBID, --imdbid IMDBID
                        Specify the IMDB ID for a movie
  -tmdb TMDBID, --tmdbid TMDBID
                        Specify theMovieDB ID for a movie
  -nm, --nomove         Overrides and disables the custom moving of file
                        options that come from output_dir and move-to
  -nc, --nocopy         Overrides and disables the custom copying of file
                        options that come from output_dir and move-to
  -nd, --nodelete       Overrides and disables deleting of original files
```

Examples
```
Movies (using IMDB ID):
manual.py -i mp4path -m imdbid
Example: manual.py -i 'C:\The Matrix.mkv' -imdb tt0133093

Movies (using TMDB ID)
manual.py -i mp4path -tmdb tmdbid
Example: manual.py -i 'C:\The Matrix.mkv' -tmdb 603

TV
manual.py -i mp4path -tv tvdbid -s season -e episode
Example: manual.py -i 'C:\Futurama S03E10.mkv' -tv 73871‎ -s 3 -e 10

Auto Single File (will gather movie ID or TV show ID / season / spisode from the file name if possible)
manual.py -i mp4path -silent
Example: manual.py -i 'C:\Futurama S03E10.mkv' -a

Directory (you will be prompted at each file for the type of file and ID)
manual.py -i directory_path
Example: manual.py -i C:\Movies

Automated Directory (The script will attempt to figure out appropriate tagging based on file name)
manual.py -i directory_path -a
Example: manual.py -i C:\Movies -a

Process a directory but manually specific TVDB ID (Good for shows that don't correctly match using the guess)
manual.py -i directory -a -tv tvdbid
Example: manual.py -i C:\TV\Futurama\ -a -tv 73871
```
You may also simply run `manual.py -i 'C:\The Matrix.mkv'` and the script will prompt you for the missing information or attempt to guess based on the file name.
You may run the script with a `--auto` or `-a` switch, which will let the script guess the tagging information based on the file name, avoiding any need for user input. This is the most ideal option for large batch file operations.
The script may also be pointed to a directory, where it will process all files in the directory. If you run the script without the `-silent` switch, you will be prompted for each file with options on how to tag, to convert without tagging, or skip.

External Cover Art
--------------
To use your own cover art instead of what the script pulls from TMDB or TVDB, simply place an image file named cover.jpg or cover.png in the same directory as the input video before processing and it will be used.

Import External Subtitles
--------------
To import external subtitles, place the .srt file in the same directory as the file to be processed. The srt must have the same name as the input video file, as well as the 3 character language code for which the subtitle is. Subtitle importing obeys the langauge rules set in autoProcess.ini, so languages that aren't whitelisted will be ignored.

Naming example:
```
input mkv - The.Matrix.1999.mkv
subtitle srt - The.Matrix.1999.eng.srt
```

Credits
--------------
This project makes use of the following projects:
- http://www.sickbeard.com/
- http://couchpota.to/
- http://sabnzbd.org/
- http://github.com/senko/python-video-converter
- http://github.com/dbr/tvdb_api
- http://code.google.com/p/mutagen/
- http://imdbpy.sourceforge.net/
- http://github.com/danielgtaylor/qtfaststart
- http://github.com/clinton-hall/nzbToMedia
- http://github.com/wackou/guessit
- http://github.com/Diaoul/subliminal

Enjoy
