Sickbeard/CouchPotato MP4 automation script.
==============

**Automatically converts mkv files downloaded by sickbeard to mp4 files, and tags them with the appropriate metadata from theTVDB. Works as an extra_script, integrated with SAB, as well as a manual post-processing script.**

**Works with CouchPotato as well, tagging with the appropriate metadata from IMDb. Requires SAB**

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
    - ffmpeg = Path to FFMPEG.exe
    - ffprobe = Path to FFPROBE.exe
    - output_directory = you may specify an alternate output directory (for example if you want to dump these mp4 files on iTunes and not have them integrated into your sickbeard collection)
    - output_extension = mp4/m4v (must be one of these 2)
    - delete_original = True/False
    - relocate_moov = True/False - relocates the MOOV atom to the beginning of the file for better streaming
    - ios-audio - creates a 2nd copy of an audio stream that will be iOS compatible (AAC Stereo) if the normal output will not be. If a stereo source stream is detected with this option enabled, an AAC stereo stream will be the only one produced (essentially overriding the codec option) to avoid multiple stereo audio stream copies in different codecs.
    - audio-codec - set your desired audio codec. Supports AAC, AC3, and DTS
    - audio-language - 3 letter language code for audio streams you wish to copy. Leave blank to copy all. Separate multiple audio streams with commas (ex: eng,spa)
    - audio-default-language - If an audio stream with an unidentified/untagged language is detected, you can default that language tag to whatever this value is (ex: eng). This is useful for many single-audio releases which don't bother to tag the audio stream as anything
    - subtitle-language - same as audio-language but for subtitles
    - subtitle-language-default - same as audio-language-default but for subtitles
    - convert-mp4 - forces the script to reprocess and convert mp4 files as though they were mkvs. Good if you have old mp4's that you want to match your current codec configuration.

SickBeard Installation Instructions
--------------
1. Open Sickbeard's config.ini in sickbeard and set your "extra_scripts" value in the general section to the full path to "python postConversion.py" using double backslashes (python C:\\Scripts\\postConversion.py). Make sure this is done while Sickbeard is not running or it will be reverted. And make sure python is registered as an environment variable/PATH
2. Set the SickBeard variables in autoProcess.ini:
    - host = Sickbeard host address (localhost)
    - port = sickbeard port (8081)
    - ssl = 0/1
    - api_key = Set this to your sickbeard API key (options -> general, enable API in sickbeard to get this key)
3. *OPTIONAL* - If you're using SAB, set your post processing script to sabToSickBeardWithConverter.py - this is not completely needed but gives the added benefit of doing the conversion from mkv to mp4 before Sickbeard sees the file in whatever folder you choose to download things to. It saves having to put in all the API information as well, and prevents the one additional refresh needed normally to have sickbeard see the properly converted file. That being said the postConversion script can handle everything on its own, so this step is just for the added benefits listed.

CouchPotato Support
--------------
1. Set your CouchPotato settings to the autoProcess.ini file
    - host = CouchPotato host address (localhost)
    - port = CouchPotato port (5050)
    - ssl = 1 if enabled, 0 if not
    - api_key = CouchPotato API Key (required)
    - username = your CouchPotato username
    - password - your CouchPotato password
2. Point your CouchPotato videos that are sent to SAB to nzbToCouchPotatoMP4.py for post processing; this will convert and tag them
3. Disable automatic checking of the renamer folder, the script will automatically notify CouchPotato when it is complete to check for new videos to be renamed and relocated. Leaving this on may cause conflicts and CouchPotato may try to relocate/rename the file before processing is completed.
    - Set "Run Every" to 0
    - Set "Force Every" to 0

Manual Script Usage
--------------
To run the script manually, simply run the manual.py file and follow the prompts it presents.
If you wish to run it via the command line (good for batch operations) follow this format. If
your autoProcess.ini specifies an output_directory this will move the final result to that dir.
If you do not want the converted/tagged file to be moved add the -nomove flag at the very end._

Newly added is the ability to let the program guess the movie or TV information.
If you would like you can use the -guess flag to target a directory structure and convert and/or tag
all the valid media files in the structure, this is great for someone who has a lot of already downloaded
mkv files and wants to do a mass convertion, if the file is already in the valid output format it will just
re-tag the file and not re-convert:

```
Movies (using IMDB ID):
manual.py mp4path -m imdbid
Example: manual.py 'C:\The Matrix.mkv' -m tt0133093

Movies (using TMDB ID)
manual.py mp4path -tmdb tmdbid
Example: manual.py 'C:\The Matrix.mkv' -tmdb 603

TV
manual.py mp4path -tv tvdbid season episode
Example: manual.py 'C:\Futurama S03E10.mkv' -tv 73871‎ 3 10

Guess
manual.py [filepath] -guess
Examples:
manual.py '/media/Futurama.s03e10.mkv' -guess
or
manual.py '/media/Iron.Man.3.2013.720p.mkv' -guess

-nomove flag
This flag overrides moving the file to the output_directory in the autoprocess.ini. It must be added
at the end of the commandline.
```

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
- https://couchpota.to/
- http://sabnzbd.org/
- https://github.com/senko/python-video-converter
- https://github.com/dbr/tvdb_api
- https://code.google.com/p/mutagen/
- http://imdbpy.sourceforge.net/
- https://github.com/danielgtaylor/qtfaststart
- https://github.com/clinton-hall/nzbToMedia
- https://github.com/wackou/guessit

Enjoy