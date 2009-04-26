from setuptools import setup, find_packages
setup(
name = 'tvnamer',
version='0.7',

author='dbr/Ben',
description='Automatic TV episode namer',
url='http://github.com/dbr/tvdb_api/tree/master',
license='GPLv2',

long_description="""\
Automatically names downloaded/recorded TV-episodes, by parsing filenames and retrieving show-names from www.thetvdb.com
Relies on tvdb_api
""",

py_modules = ['tvnamer'],
entry_points = {
    'console_scripts':[
        'tvnamer = tvnamer:main'
    ]
},

setup_requires = ['tvdb_api'],

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
