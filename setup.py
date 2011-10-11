from distutils.core import setup
import qtfaststart

long_description = open('README.rst').read()

setup(
    name='qtfaststart',
    version=qtfaststart.VERSION,
    description='Quicktime atom positioning in Python for fast streaming.',
    long_description=long_description,
    author='Daniel G. Taylor',
    author_email='dan@programmer-art.org',
    url='https://github.com/gtaylor/qtfaststart',
    license='GNU General Public License (GPL)',
    platforms=["any"],
    provides=['qtfaststart'],
    packages=[
        'qtfaststart',
    ],
    scripts=['bin/qtfaststart'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Multimedia :: Video :: Conversion',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
