Sickbeard MP4 automation script.
==============

**Automatically converts mkv files downloaded by sickbeard to mp4 files, and tags them with the appropriate metadata from theTVDB. Works as an extra_script, integrated with SAB, as well as a manual post-processing script.**

- Requires Python 2.7 *(Does NOT work with Python 3)*
- Only tested on Windows

Installation Instructions
--------------
1. Open Sickbeard's config.ini in sickbeard and set your "extra_scripts" value in the general section to the full path to postConversion.bat using double backslashes (C:\\Scripts\\postConversion.cmd). Make sure this is done while Sickbeard is not running or it will be reverted.
2. Rename tvdb_mp4.ini.default to tvdb_mp4.ini and set the variables:
    ip = probably localhost
    port = sickbeard port (8081)
    ssl = True/False
    api_key = Set this to your sickbeard API key (options -> general, enable API in sickbeard to get this key)
    ffmpeg = Path to FFMPEG.exe
    ffprobe = Path to FFPROBE.exe
    output_directory = you may specify an alternate output directory (for example if you want to dump these mp4 files on iTunes and not have them integrated into your sickbeard collection)
    output_extension = mp4/m4v (must be one of these 2)
    delete_original = True/False
3. *OPTIONAL* - If you're using SAB, set your post processing script to sabToSickBeardWithConverter.py - this is not completely needed but gives the added benefit of doing the conversion from mkv to mp4 before Sickbeard sees the file in whatever folder you choose to download things to. It saves having to put in all the API information as well, and prevents the one additional refresh needed normally to have sickbeard see the properly converted file. That being said the postConversion script can handle everything on its own, so this step is just for the added benefits listed.

Enjoy