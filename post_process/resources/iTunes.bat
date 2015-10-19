@echo off
:: Make sure "Edit>Preferences>Advanced>Copy files to iTunes Media folder when adding to library" is unchecked before implementing this. 
:: Pull file path from SMA
set var=%MH_FILES%
:: Remove [] from Path pulled from SMA
set var2=%var:~1,-1%
:: Put the path to your itunes.exe, This MUST be in quotes if there is a space in the path. i.e. "C:\Program Files\iTunes\iTunes.exe"
:: Tell iTunes to open and add file to library
(start "C:\Program Files\iTunes\iTunes.exe" %var2%)
