from setuptools import setup, find_packages
setup(
name = 'tvnamer',
version='0.2',

author='dbr/Ben',
description='Automatic TV episode namer',
url='http://github.com/dbr/tvdb_api/tree/master',
license='GPLv2',

long_description="""\
Automatically names downloaded/recorded TV-episodes, by parsing filenames and retriving shownames from www.thetvdb.com
Includes tvdb_api - an easy to use API interface to TheTVDB.com
""",

scripts = ['tvdb_api.py', 'tvnamer.py'],
install_requires=['BeautifulSoup'],
)