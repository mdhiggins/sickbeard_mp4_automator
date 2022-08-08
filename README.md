SMA Conversion/Tagging Automation Script
==============

**Automatically converts media files downloaded by various programs to a standardized format, and tags them with the appropriate metadata from TMDB if the container supports tagging.**

![The Matrix](https://user-images.githubusercontent.com/3608298/76170063-e415c300-6154-11ea-88cd-d26653a47cc5.PNG)

Works on Windows, OSX, and Linux. Despite the name works with much more than just Sickbeard and handles more than MP4s

Integration
--------------
### Media Managers Supported
- [Sonarr](#sonarr-setup)
- [Radarr](#radarr-setup)
- [Sickbeard](#sickbeard-setup)
- [SickRage](#sickrage-setup)

### Downloaders Supported
- [NZBGet](#nzbget-setup)
- [SABNZBD](#sabnzbd-setup)
- [Deluge Daemon](#deluge-daemon-setup)
- [uTorrent](#utorrent-setup)
- [qBittorrent](#qbittorrent-setup)

Dependencies
--------------
- [Python 3](https://www.python.org/)
- [FFmpeg](https://ffmpeg.org/)
- [Python Packages](https://github.com/mdhiggins/sickbeard_mp4_automator/wiki/Dependencies)

Default Settings
--------------
- Container - MP4
- Video - H264
- Audio - AAC 2.0 with additional AC3 track when source has >2 channels (ex 5.1)
- Subtitles - mov_text

Docker
--------------
Two official Docker containers are maintained for Radarr and Sonarr with SMA included. These are meant to work with **completed download handling** enabled. See the respective Docker Hub pages for details
- https://hub.docker.com/r/mdhiggins/sonarr-sma
- https://hub.docker.com/r/mdhiggins/radarr-sma

General Configuration
--------------
1. Download or compile FFmpeg 
2. Install [requirements/dependencies](#dependencies)
3. Rename `setup\autoProcess.ini.sample` to `autoProcess.ini` and place inside your `config` directory (or attempt to run the script which will generate a new config file if absent)
4. Set the [configuration options](https://github.com/mdhiggins/sickbeard_mp4_automator/wiki/autoProcess-Settings) to your desired output and include the path of your new FFmpeg / FFprobe binaries
5. Run [manual.py](#manual-script-usage) and test out a conversion
6. Configure direct integration using the instructions below

Sonarr Setup
--------------
1. Set your [Sonarr settings](https://github.com/mdhiggins/sickbeard_mp4_automator/wiki/autoProcess-Settings#sonarr) in autoProcess.ini
2. Browse to the Settings>Download Client tab and enable advanced settings [Show].
3. Setup the postSonarr.py script via Settings > Connect > Connections > + (Add)
    - `name` - postSonarr
    - `On Grab` - No
    - `On Download` \ `On Import` - Yes
    - `On Upgrade` - Yes
    - `On Rename` - No
    - `On Movie Delete` - No
    - `On Movie File Delete` - No
    - `On Health Issue` - No
    - `Path` - Full path to your python executable
    - `Arguments` - Full path to `postSonarr.py`
    - For Sonarr V3 you'll need to make a .sh or .bat file to combine your path to python and script
4. **OPTIONAL** If you desire to convert the file before it is handed back to Sonarr, disable 'Completed Download Handling' in Sonarr settings and configure your download client to use its included script (scroll down to your relevant download client in the readme). The script will trigger a specific path re-scan, allowing the conversion to be completed before Sonarr starts moving stuff around. **You must use either a download script or enabled Completed Download Handling. If neither are used the file will never be passed back**

Radarr Setup
--------------
1. Set your [Radarr settings](https://github.com/mdhiggins/sickbeard_mp4_automator/wiki/autoProcess-Settings#radarr) in autoProcess.ini
2. Browse to the Settings>Download Client tab and enable advanced settings [Show].
3. Setup the postRadarr.py script via Settings > Connect > Connections > + (Add)
    - `name` - postRadarr
    - `On Grab` - No
    - `On Download` / `On Import` - Yes
    - `On Upgrade` - Yes
    - `On Rename` - No
    - `On Movie Delete` - No
    - `On Movie File Delete` - No
    - `On Health Issue` - No
    - `Path` - Full path to your python executable
    - `Arguments` - Full path to `postRadarr.py`
    - For Radarr V3 you'll need to make a .sh or .bat file to combine your path to python and script
4. **OPTIONAL** If you desire to convert the file before it is handed back to Radarr, disable 'Completed Download Handling' in Radarr settings and configure your download client to use its included script (scroll down to your relevant download client in the readme). The script will trigger a specific path re-scan, allowing the conversion to be completed before Radarr starts moving stuff around. **You must use either a download script or enabled Completed Download Handling. If neither are used the file will never be passed back**

Sickbeard Setup
--------------
1. Open Sickbeard's config.ini in Sick Beard installation folder
    - Set "extra_scripts" value in the general section to the full path to "python postSickbeard.py" using double backslashes
        - Example: `C:\\Python27\\python C:\\Scripts\\postSickbeard.py`
        - Make sure this is done while Sick Beard is not running or it will be reverted
2. Set your [SickBeard settings](https://github.com/mdhiggins/sickbeard_mp4_automator/wiki/autoProcess-Settings#sickbeard) in autoProcess.ini

SickRage Setup
--------------
1. Open the configuration page in Sickrage and scroll down to the option labelled "Extra Scripts". Here enter the path to python followed by the full script path. Examples:
    - `C:\\Python27\\python.exe C:\\sickbeard_mp4_automator\\postSickbeard.py`
    - `/usr/bin/python /home/user/sickbeard_mp4_automator/postSickbeard.py`
2. Set the [Sickrage settings](https://github.com/mdhiggins/sickbeard_mp4_automator/wiki/autoProcess-Settings#sickrage) in autoProcess.ini

NZBGet Setup
--------------
1. Copy the script NZBGetPostProcess.py to NZBGet's script folder.
    - Default location is /opt/nzbget/scripts/
2. Start/Restart NZBGet
3. Configure NZBGETPOSTPROCESS
    - Access NZBGet's WebUI
        - Default `localhost:6789`
    - Go to `Settings`
    - Select `NZBGETPOSTPROCESS` option at the bottom of the left hand navigation panel and configure the options
        - `MP4_FOLDER` - default `~/sickbeard_mp4_automator/` - Location of the script. Use full path with trailing backslash.
        - `SHOULDCONVERT` - `True`/`False` - Convert file before passing to destination
        - `SONARR_CAT` - default `sonarr` - category of downloads that will be passed to Sonarr
        - `SICKBEARD_CAT` - default `sickbeard` - category of downloads that will be passed to Sickbeard
        - `SICKRAGE_CAT` - default `sickrage` - category of downloads that will be passed to Sickrage
        - `BYPASS_CAT` - default `bypass` - category of downloads that may be converted but won't be passed on further
    - Save changes
    - Reload NZBGet
4. When assigning categories in NZBGet and your chosen media manager, ensure they match the label settings specified here so that file will be passed back to the appropriate location.
    - In the relevant category set `PostScript` to NZBGetPostProcess.py to ensure SMA is called.

*Not required if using Completed Download Handling with Sonarr/Radarr*

SABNZBD Setup
--------------
1. Set your [SABNZBD settings](https://github.com/mdhiggins/sickbeard_mp4_automator/wiki/autoProcess-Settings#sabnzbd) in autoProcess.ini
2. Point SABNZBD's script directory to the root directory where you have extract the script.
3. Configure categories. Categories will determine where the download is sent when it is finished
    - `Settings > Categories`
    - Configure `name` to match the settings from the `SABNZBD` section of `autoProcess.ini`
        - Default `sickbeard`
        - Default `sickrage`
        - Default `sonarr`
        - Default `bypass`
    - Select the SABPostProcess.py script
    - Save EACH category
4. Verify that whatever media manager you are using is assigning the label to match the label settings specified here so that file will be passed back to the appropriate location

*Not required if using Completed Download Handling with Sonarr/Radarr*

Deluge Daemon Setup
--------------
1. Create username and password for deluge daemon
    - Navigate to your deluge configuration folder
        - `%appdata%\Roaming\Deluge` in Windows
        - `/var/lib/deluge/.config/deluge/` in Linux
    - Open the `auth` file
    - Add a username and password in the format `<username>:<password>:<level>`. Replace <username> and <password> with your choice and level with your desired authentication level. Default level is `10`. Save auth.
        - Ex: `sampleuser:samplepass:10`
2. Start/Restart deluged
    - *deluged* not <i>deluge</i>
    - If you're running Deluge on Windows and not setting up the daemon as a service, you can trigger the daemon to run in the background by disabling *Classic Mode* in your Deluge preferences under the *Interface* section
3. Access the WebUI
    - Default port is `8112`
    - Default password is `deluge`
4. Enabled the `Execute` plugin
    - Add event for `Torrent Complete`
    - Set path to the full path to `delugePostProcess.py` or a batch file wrapper that passes command line arguments for Windows users with difficulty executing python files directly
5. Set your [Deluge settings](https://github.com/mdhiggins/sickbeard_mp4_automator/wiki/autoProcess-Settings#deluge) in autoProcess.ini
6. Verify that whatever downloader you are using is assigning the label to match the label settings specified here so that file will be passed back to the appropriate location

*Not required if using Completed Download Handling with Sonarr/Radarr*

uTorrent Setup
--------------
1. Launch uTorrent
2. Set `Run Program` option
    - Go to `Options > Preferences > Advanced > Run Program`
    - Point to `uTorrentPostProcess.py` with command line parameters: `%L %T %D %K %F %I %N` in that exact order.
3. Set your [uTorrent settings](https://github.com/mdhiggins/sickbeard_mp4_automator/wiki/autoProcess-Settings#utorrent) in autoProcess.ini
4. Verify that whatever media manager you are using is assigning the label to match the label settings specified here so that file will be passed back to the appropriate location

*Not required if using Completed Download Handling with Sonarr/Radarr*

qBittorrent Setup
--------------
1. Launch qBittorrent
2. Set `Run Program` option
    - Go to `Tools > Options > Run external program on torrent completion`
    - Point to `qBittorrentPostProcess.py` with command line parameters: `"%L" "%T" "%R" "%F" "%N" "%I"` in that exact order.
3. Set your [qBittorrent settings](https://github.com/mdhiggins/sickbeard_mp4_automator/wiki/autoProcess-Settings#qbittorrent) in autoProcess.ini
4. Verify that whatever media manager you are using is assigning the label to match the label settings specified here so that file will be passed back to the appropriate location

*Not required if using Completed Download Handling with Sonarr/Radarr*

Plex Notification
--------------
Send a Plex notification as the final step when all processing is completed. This feature prevents a file from being flagged as "in use" by Plex before processing has completed.
1. Disable automatic refreshing on your Plex server
    - `Settings > Server > Library` and disable `Update my library automatically` and `Update my library periodically`.
3. Set your [Plex settings](https://github.com/mdhiggins/sickbeard_mp4_automator/wiki/autoProcess-Settings#plex) in autoProcess.ini

If you have secure connections enabled with Plex you will need to add your local IP addresss that the refresh requests are coming from to allow them to trigger the refresh, otherwise you will get an HTTP error. You can alternatively not force encryption by changing `Secure Connections` from `Required` to `Preferred` but this is not recommended as its less secure.

Found under Plex Server Settings > Network > Advanced
![image](https://user-images.githubusercontent.com/3608298/52716936-e61b4b80-2f6d-11e9-8537-83ab9321948b.png)

Override Configuration Path
--------------
If for some reason you need to override the path to autoProcess.ini (for virtual environments, containers, etc) you can use the environment variable `SMA_CONFIG` to the absolute path

Post Process Scripts
--------------
- See https://github.com/mdhiggins/sickbeard_mp4_automator/blob/master/post_process/post_process.md

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
  --config              Specify an alternate configuration file location
  -a, --auto            Enable auto mode, the script will not prompt you for
                        any further input, good for batch files. It will guess
                        the metadata using guessit
  -tmdb TMDBID, --tmdbid TMDBID
                        Specify the TMDB ID for media
  -tvdb TVDBID, --tvdbid TMBDID
                        Specify the TVDB ID for media
  -imdb IMDBID, --imdbid IMDBID
                        Specify the IMDB ID for media
  -s SEASON, --season SEASON
                        Specifiy the season number
  -e EPISODE, --episode EPISODE
                        Specify the episode number
  -nm, --nomove         Overrides and disables the custom moving of file
                        options that come from output_dir and move-to
  -m, --moveto          Override move-to value setting in autoProcess.ini
                        changing the final destination of the file
  -nc, --nocopy         Overrides and disables the custom copying of file
                        options that come from output_dir and move-to
  -nt, --notag          Overrides and disables tagging when using the
                        automated option
  -to, --tagonly        Only tag without conversion
  -nd, --nodelete       Overrides and disables deleting of original files
  -pr, --preserverelative
                        Preserves relative directories when processing
                        multiple files using the copy-to or move-to
                        functionality
  -pse, --processsameextensions   
                        Overrides process-same-extensions setting in 
                        autoProcess.ini enabling the reprocessing of files
  -fc, --forceconvert   Overrides force-convert setting in autoProcess.ini and 
                        also enables process-same-extenions if true forcing the conversion of files
  -oo, --optionsonly    Display generated conversion options only, do not perform conversion
  -cl, --codeclist      Print a list of supported codecs and their paired FFMPEG encoders
  -pa, --processedarchive
                        Specify a processed list/archive so already processed files are skipped
```

Examples
```
Movies (using IMDB ID):
manual.py -i mp4path -imdb imdbid
Example: manual.py -i "C:\The Matrix.mkv" -imdb tt0133093

Movies (using TMDB ID)
manual.py -i mp4path -tmdb tmdbid
Example: manual.py -i "C:\The Matrix.mkv" -tmdb 603

TV
manual.py -i mp4path -tvdb tmbdid -s season -e episode
Example: manual.py -i "C:\Futurama S03E10.mkv" -tvdb 73871‎ -s 3 -e 10

Auto Single File (will gather movie ID or TV show ID / season / spisode from the file name if possible)
manual.py -i mp4path -a
Example: manual.py -i "C:\Futurama S03E10.mkv" -a

Directory (you will be prompted at each file for the type of file and ID)
manual.py -i directory_path
Example: manual.py -i C:\Movies

Automated Directory (The script will attempt to figure out appropriate tagging based on file name)
manual.py -i directory_path -a
Example: manual.py -i C:\Movies -a

Process a directory but manually specific TVDB ID (Good for shows that don't correctly match using the guess)
manual.py -i directory -a -tvdb tvdbid
Example: manual.py -i C:\TV\Futurama\ -a -tvdb 615
```
You may also simply run `manual.py -i 'C:\The Matrix.mkv` and the script will prompt you for the missing information or attempt to guess based on the file name.
You may run the script with a `--auto` or `-a` switch, which will let the script guess the tagging information based on the file name, avoiding any need for user input. This is the most ideal option for large batch file operations.
The script may also be pointed to a directory, where it will process all files in the directory. If you run the script without the `-a` switch, you will be prompted for each file with options on how to tag, to convert without tagging, or skip.

External Cover Art
--------------
To use your own cover art instead of what the script pulls from TMDB or TVDB, simply place an image file  in the same directory as the input video with the same name before processing and it will be used. Must be `jpg` or `png`

Import External Subtitles
--------------
To import external subtitles, place the .srt file in the same directory as the file to be processed. The srt must have the same name as the input video file, as well as the language code for which the subtitle is. Subtitle importing obeys the langauge rules set in autoProcess.ini, so languages that aren't whitelisted will be ignored.

Naming example:
```
input mkv - The.Matrix.1999.mkv
subtitle srt - The.Matrix.1999.eng.srt
```

Credits
--------------
This project makes use of, integrates with, or was inspired by the following projects:
- http://www.ffmpeg.org/
- http://www.python.org/
- http://www.sickbeard.com/
- http://sabnzbd.org/
- https://nzbget.net/
- https://www.deluge-torrent.org/
- https://www.qbittorrent.org/
- http://github.com/senko/python-video-converter
- https://github.com/celiao/tmdbsimple
- https://github.com/quodlibet/mutagen
- http://github.com/danielgtaylor/qtfaststart
- http://github.com/wackou/guessit
- http://github.com/Diaoul/subliminal
- http://sonarr.tv/
- http://radarr.video/
- https://github.com/ratoaq2/cleanit

## Enjoy
