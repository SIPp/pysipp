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


with open("README.md") as f:
    readme = f.read()


setup(
    name="pysipp",
    version="0.1.0",
    description="A SIPp scenario launcher",
    long_description=readme,
    long_description_content_type="text/markdown",
    license="GPLv2",
    author="Tyler Goodlet",
    author_email="jgbt@protonmail.com",
    url="https://github.com/SIPp/pysipp",
    platforms=["linux"],
    packages=["pysipp", "pysipp.cli"],
    install_requires=["pluggy>=1.0.0"],
    tests_require=["pytest"],
    entry_points={
        "console_scripts": ["sippfmt=pysipp.cli.sippfmt:main"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Utilities",
    ],
)
