Tutorial
========

Most of the tasks (video probing, converting, thumbnail generation)
can be done using the high-level Converter object.

Creating the Converter object
-----------------------------

First we need to import the module and create the object::

    >>> from converter import Converter
    >>> c = Converter()

By default, the converter uses ffmpeg and ffprobe binaries in your path. If
it should use them from another location, you can specify the paths to them
in the Converter constructor.

Getting existing multimedia file properties
-------------------------------------------

Probing the media file will return a :class:`MediaInfo` object, containing
various information about the file format, media streams, codecs and properties::

    >>> info = c.probe('test1.ogg')
    >>> info.format.format
    'ogg'
    >>> info.format.duration
    33.00
    >>> len(info.streams)
    2
    >>> info.video.codec
    'theora'
    >>> info.video.video_width
    720
    >>> info.video.video_height
    400
    >>> info.audio.codec
    'vorbis'
    >>> info.audio.audio_channels
    2

A full list of properties can be found in :class:`MediaFormatInfo` and
:class:`MediaStreamInfo` documentation.

Converting a video into another format
--------------------------------------

To convert a media file into some other format (or to use some other codecs),
you need to create a dictionary (map) of options specifying what to convert to.

The options dictionary looks like this::

    {
        'format': 'mkv',
        'audio': {
            'codec': 'mp3',
            'samplerate': 11025,
            'channels': 2
        },
        'video': {
            'codec': 'h264',
            'width': 720,
            'height': 400,
            'fps': 15
        }
    }

The full list of options can be found in :class:`Converter` documentation.

To prepare the conversion process::

    >>> conv = c.convert('test1.ogg', '/tmp/output.ogg', options)

This won't start the conversion, it will just prepare everything and return a
generator. To run the conversion process, iterate the generator until it's finished.
On each iteration, the generator will yield a timecode, specifying how far into the
media file is the conversion process at the moment (ie. at which second in the movie
is the process).

To just drive the conversion without using the timecode information:

    >>> for timecode in conv:
    ...    pass


Getting audio from a video file
-------------------------------

To just get the audio content from a video file, you can use the conversion
as above, specifying in the options that the video should be dropped::

    {
        'format': 'mp3',
        'audio': {
            'codec': 'mp3',
            'bitrate': '22050',
            'channels': 1
        }
    }

Since the video is not specified in the output, the video stream will be dropped.
Likewise, you can drop the audio stream from the output.

If you just want to copy audio or video stream as is, without conversion, you can
do that by specifying the 'copy' codec.


Creating a thumbnail
--------------------

To create a thumbnail form a video file (from 10 seconds in the movie)::

    >>> c.thumbnail('test1.ogg', 10, '/tmp/shot.png')

You can specify the screenshot dimensions:

    >>> c.thumbnail('test1.ogg', 10, '/tmp/shot.png', '320x200')
