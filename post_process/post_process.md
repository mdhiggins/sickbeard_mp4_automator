# Post Processing Scripts

Post processing scripts go in this folder

Samples can be found in `./setup/post_process`

Post Process Scripts
--------------
The script suite supports the ability to write your own post processing scripts that will be executed when all the final processing has been completed. All scripts in the `./post_process` directory will be executed if the `post-process` option is set to `True` in `autoProcess.ini`. Scripts within the `./post_process/resources` directory are protected from execution if additional script resources are required.

The following environmental variables are available for usage:
- `SMA_FILES` - JSON Array of all files created by the post processing script. The first file in the array is the primary file, and any additional files are copies created by the copy-to option
- `SMA_TMDBID` - TMDB ID of file 
- `SMA_SEASON` - Season number if file processed was a TV show
- `SMA_EPISODE` - Episode number if files processed was a TV show
A sample script as well as an OS X 'Add to iTunes' script (`iTunes.py`) have been provided in `.setup/post_process`.

*Special thanks to @jzucker2 for providing much of the initial code for this feature*
