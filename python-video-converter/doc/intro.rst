Introduction
============

Video Converter is a Python module for converting video files from one
format and codec to another.

It uses the `FFmpeg <http://www.ffmpeg.org/>`_ multimedia framework for
actual file processing, and adds an easy-to-use API for probing and
converting media files on top of it.

Licensing and Patents
---------------------

Although FFmpeg is licensed under LGPL/GPL, Video Converter only invokes
the existing ffmpeg executables on the system (ie. doesn't link to the
ffmpeg libraries), so it doesn't need to be LGPL/GPL as well.

The same applies to patents. If you're in a country which recognizes
software patents, it's up to you to ensure you're complying with the
patent laws. Please read the
`FFMpeg Legal FAQ <http://www.ffmpeg.org/legal.html>`_ for more information.
