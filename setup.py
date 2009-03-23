from setuptools import setup, find_packages
setup(
name = 'tvnamer',
version='0.6',

author='dbr/Ben',
description='Automatic TV episode namer',
url='http://github.com/dbr/tvdb_api/tree/master',
license='GPLv2',

long_description="""\
Automatically names downloaded/recorded TV-episodes, by parsing filenames and retrieving show-names from www.thetvdb.com
Includes tvdb_api - an easy to use API interface to TheTVDB.com
""",

py_modules = ['tvdb_api', 'tvnamer', 'tvdb_ui', 'tvdb_exceptions', 'cache'],
entry_points = {
    'console_scripts':[
        'tvnamer = tvnamer:main'
    ]
},

classifiers=[
    "Environment :: Console",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: GNU General Public License (GPL)",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Topic :: Multimedia",
    "Topic :: Utilities"
]
)
