#!/usr/bin/env python

import codecs
import os
from setuptools import find_packages, setup

with open(os.path.join("battleships","__init__.py"), "r") as fh:
    while True:
        line = fh.readline()
        if line.startswith("__version__"):
            VERSION = line.split("=")[1].strip().replace('"','').replace("'",'')
            break

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, 'README.rst'), encoding='utf8') as fh:
    long_description = fh.read()

with open('requirements.txt') as fobj:
    install_requires = [line.strip() for line in fobj]

setup(
    name='battleships',
    version=VERSION,
    description='Battleships; the classic game for two human players',
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url='https://github.com/smerckel/battleships',
    author='Lucas Merckelbach',
    author_email='lucas.merckelbach@tutanota.de',
    license='MIT',
    packages=['battleships'],
    #packages=find_packages(where='.', exclude=['tests', 'docs'])
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Games',
        'License :: OSI Approved :: MIT License',
        'Environment :: Console',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.6',
    ],
    keywords=['games', 'battleships', 'zeeslag'],
    install_requires=install_requires,
    include_package_data=True,
    entry_points = {'console_scripts':['battleships = battleships.battleships:main',
                                       'battleships_server = battleships.battleships_server:main'],
                    'gui_scripts':[]}
)
