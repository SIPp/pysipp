#!/usr/bin/env python
#
# Copyright (C) 2015 Tyler Goodlet
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Authors : Tyler Goodlet

from setuptools import setup


with open('README.md') as f:
    readme = f.read()


setup(
    name="pysipp",
    version='0.1.alpha',
    description='pysipp is Python wrapper for configuring and launching SIPp scenarios for use in'
                ' automated testing',
    long_description=readme,
    license='GPLv2',
    author='Tyler Goodlet',
    author_email='tgoodlet@gmail.com',
    url='https://github.com/tgoodlet/pysipp',
    platforms=['linux'],
    packages=['pysipp'],
    extras_require={
        'testing': ['pytest'],
    },
    # use_2to3 = False
    # zip_safe=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2',
        'Operating System :: Linux',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Utilities',
    ],
)
