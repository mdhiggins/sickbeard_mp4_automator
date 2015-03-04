MP4 Conversion/Tagging Automation Script.
==============

**Automatically converts media files downloaded by various to mp4 files, and tags them with the appropriate metadata from theTVDB or TMDB.**

Programs currently supported include:
- Sickbeard
- CouchPotato
- Sonarr (tagging not supported, see below)
- SABNZBD
- NZBGet
- uTorrent


Requirements
--------------
- Python 2.7 *(Does NOT work with Python 3)*
- FFMPEG and FFPROBE binaries
- Some scripts require the python module <i>REQUESTS</i>.
- Python setup_tools
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
    - `max-audio-channels` = Sets a maximum number of audio channels. This may provide an alternative to the iOS audio option, where instead users can simply select the desired output codec and the max number of audio channels without the creation of an additional audio track. 
    - `video-codec` = set your desired video codecs. May specify multiple comma separated values (ex: h264, x264). The first value specified will be the default conversion choice when an undesired codec is encountered; any codecs specified here will be remuxed/copied rather than converted. 
    - `video-bitrate` = allows you to set a maximum video bitrate in Kbps. If the source file exceeds the video-bitrate it will be transcoded to the specified video-bitrate, even if they source file is already in the correct video codec. If the source file is in the correct video codec and does not exceed the video-bitrate setting, then it will be copied without transcoding. Leave blank to disable this setting.
    - `audio-codec` = set your desired audio codecs. May specify multiple comma separated values (ex: ac3, aac). The first value specified will be the default conversion choice when an undesired codec is encountered; any codecs specified here will be remuxed/copied rather than converted. 
    - `audio-channel-bitrate` = set the bitrate for each audio channel. Default is 256. Setting this value to 0 will attempt to mirror the bitrate of the audio source, but this can be unreliable as bitrates vary between different codecs.
    - `audio-language` = 3 letter language code for audio streams you wish to copy. Leave blank to copy all. Separate multiple audio streams with commas (ex: eng,spa)
    - `audio-default-language` = If an audio stream with an unidentified/untagged language is detected, you can default that language tag to whatever this value is (ex: eng). This is useful for many single-audio releases which don't bother to tag the audio stream as anything
    - `subtitle-language` = same as audio-language but for subtitles. Set to `nil` to disable copying of subtitles.
    - `subtitle-language-default` = same as audio-language-default but for subtitles
    - `convert-mp4` = forces the script to reprocess and convert mp4 files as though they were mkvs. Good if you have old mp4's that you want to match your current codec configuration.
    - `fullpathguess` = True/False - When manually processing a file, enable to guess metadata using the full path versus just the file name. (Files shows placed in a 'Movies' folder will be recognized as movies, not as TV shows for example.)
    - `tagfile` = True/False - Enable or disable tagging file with appropriate metadata after encoding.
    - `tag-language` = en - Set your tag language for TMDB/TVDB entries metadata retrieval. Use either 2 or 3 character language codes.
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

Sonarr Support (Tagging Not Supported)
--------------
1. ** YOU MUST INSTALL THE PYTHON REQUESTS LIBRARY ** Run "pip install requests" or "easy_install requests"
2. Set your Sonarr settings in the autoProcess.ini file
    - `host` = Sonarr host address (localhost)    #Settings/General/Start-Up
    - `port` = Sonarr port (8989)                 #Settings/General/Start-Up
    - `ssl` = 1 if enabled, 0 if not                #Settings/General/Security
    - `apikey` = Sonarr API Key (required)       #Settings/General/Security
    - `web_root` = URL base empty or e.g. /tv #Settings/General/Start-Up
2. Browse to the Settings>Download Client tab and enable advanced settings [Show].
3. Set the {Drone Factory Interval} to 0 to disable it. (NZBGet will trigger a specific path re-scan, allowing the mp4 conversion to be completed before Sonarr starts moving stuff around).
    - Sonarr does not currently support post processing scripts so tagging is not currently supported.

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
3. If you're using one of the post download scripts ([SAB|NZBGet|uTorrent]PostProcess.py), disable automatic checking of the renamer folder, the script will automatically notify Couch Potato when it is complete to check for new videos to be renamed and relocated. Leaving this on may cause conflicts and CouchPotato may try to relocate/rename the file before processing is completed.
    - Set `Run Every` to `0` 
    - If you aren't using one of these scripts and are using an unsupport downloader, you will need to have CouchPotato periodically check the folder for files
4. Point your Couch Potato videos that are sent to SAB to SABPostProcess.py for post processing with conversion prior to CP begin notified of completion. Similarly use NZBGetPostProcess.py for NZBGet. Make sure you configure your SAB/NZBGet categories so that they match with the categories configured for the script.

NZBGet
--------------
1. Copy the script NZBGetPostProcess.py to NZBGet's script folder. (default location is ~/downloads/scripts/)
2. In NZBGet's web GUI, go to [Settings] and the newly created {NZBGETPOSTPROCESS} option. Fill in the MP4 automator folder path with the full path. (default ~/sickbeard_mp4_automator/) I suggest the full path and requires the trailing backslash "/".
3. You may change or set your appropriate category names to correspond with the application you wish to send the files to (CouchPotato, Sickbeard, Sonarr, Bypass) in this same settings area. Make sure these categories match. The Bypass category is for those that wish to convert the file without additional post processing.
4. You may set the `convert` option to enable conversion before the file is passed on to the next step.
5. Save and reload NZBGet

SAB
--------------
1. Point SABNZBD's script directory to the root directory where you have extract the script.
2. Make sure your categories are set and match the categories specified in the SABNZBD section of autoProcess.ini. Set the script for each category to `SABPostProcess.py`
3. Bypass category can be used for users that just want to convert the files without passing them for additional processing
4. Press save for each category
5. You may set the `convert` option to enable conversion before the file is passed on to the next step.

uTorrent Support
--------------
1. ** YOU MUST INSTALL THE PYTHON REQUESTS LIBRARY ** Run "pip install requests" or "easy_install requests"
2. `uTorrentPostProcess.py` is the file you'll be using here. This script will allow post processing of torrent files with optional conversion and will forward the converted files to either Sickbeard, CouchPotato, Sonarr, or Bypass depending on the corresponding label of the torrent. Bypass is used when only conversion is desired and you don't want to pass the file for further processing.
3. Enable uTorrent Web UI.
4. uTorrent must be set up with the following post command options: ```#Args: %L %S %D %K %F %S %I``` Picture: http://i.imgur.com/7eADkCI.png
5. Set your uTorrent settings in autoProcess.ini
    - Set `sickbeard-label` `couchpotato-label` and `sonarr-label` to match your appropriate uTorrent label. Files without this corrrect label will be ignored.
    - Set `webui` to True/False. If True the script can change the state of the torrent.
    - Set `action_before` to stop/pause or any other action from http://help.utorrent.com/customer/portal/articles/1573952-actions---webapi
    - Set `action_after` to start/stop/pause/unpause/remove/removedata or any other action from http://help.utorrent.com/customer/portal/articles/1573952-actions---webapi
    - Set `hostname` to your uTorrent Web UI URL, eg http://localhost:8080/ including the trailing slash.
    - Set `username` to your uTorrent Web UI username
    - Set `password` to your uTorrent Web UI password

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
  -pr, --preserveRelative
                        Preserves relative directories when processing
                        multiple files using the copy-to or move-to
                        functionality
  -cmp4, --convertmp4   Overrides convert-mp4 setting in autoProcess.ini 
                        enabling the reprocessing of mp4 files
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

Common Errors
--------------
- `ImportError: No module named pkg_resources` - you need to install setuptools for python. See here: https://pypi.python.org/pypi/setuptools#installation-instructions

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
