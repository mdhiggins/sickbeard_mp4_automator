---
name: Bug report
about: Include all sections
title: ''
labels: ''
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**Command or context you are trying to run**
For manual.py include the full command, for integrated commands please include relavent logs from those programs (IE for postSonarr.py please include relevant Sonarr logs)

**autoProcess.ini settings**
**Please sensor API keys/private information but include all other settings**

**Log files**
Include log files *for the specific job (not just a dump of all your logs for the past month)* that's causing the issue. Please turn on [debug level logging](https://github.com/mdhiggins/sickbeard_mp4_automator/wiki/Debug-Level-Logging)
Log files are found in your script root config folder `./sma/config/sma.log`

**FFMpeg headers**
 - Run ffmpeg and post the headers, example [headers]https://github.com/mdhiggins/sickbeard_mp4_automator/wiki/FFMPEG-Headers

**System Information**
 - OS: [e.g. Windows]
 - Python version
 - Docker config (if relevant)

**Expected behavior**
A clear and concise description of what you expected to happen.

**Additional context**
Add any other context about the problem here.

*Issues posted without any logs or autoProcess settings will be closed*
