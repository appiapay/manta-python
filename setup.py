# -*- coding: utf-8 -*-
# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018 Alessandro Viganò
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

from setuptools import setup

from manta import MANTA_VERSION

here_dir = os.path.dirname(__file__)
with open(os.path.join(here_dir, 'requirements.txt')) as req_file:
    requirements = req_file.read().splitlines()


setup(
    name='manta',
    version=MANTA_VERSION,
    packages=['manta'],
    url='',
    license='',
    author='Alessandro Viganò',
    author_email='alvistar@gmail.com',
    description='',
    install_requires=requirements
)
