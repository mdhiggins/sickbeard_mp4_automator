Installation and Requirements
=============================

Video Converter requires a working Python installation, and a fairly recent
version of ffmpeg libraries and utilities (ffmpeg and ffprobe).

Video Converter installation
----------------------------

To build the library, run::

    python setup.py build

To run automated tests::

    python setup.py test

To create this documentation::

    python setup.py doc

To install the library::

    python setup.py install


Custom compiling ffmpeg
-----------------------

The supported formats and codecs depend on the support compiled in to ffmpeg.
Many distributors choose to enable only a subset of the supported codecs, so
if the version installed by your OS/distribution doesn't support a particular
feature, it's advisable to recompile ffmpeg yourself.

The latest development version of FFmpeg can be downloaded from the
`official git repository <http://git.videolan.org/?p=ffmpeg.git>`_.

To build all the codecs that Video Converter can use, you can use
the following configure options::

       ./configure --prefix=${TARGET_PREFIX} \
            --extra-cflags=-I${TARGET_PREFIX}/include \
            --extra-ldflags=-L${TARGET_PREFIX}/lib \
            --enable-libmp3lame \
            --enable-libvorbis \
            --enable-libtheora \
            --enable-libx264 --enable-gpl \
            --enable-libvpx \
            --enable-libxvid
        make

You will need to install (either the version built by your OS distributor
if it's new enough, or a custom-compiled one) the mentioned extra libraries so
ffmpeg can make use of them.


