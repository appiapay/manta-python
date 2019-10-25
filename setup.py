# -*- coding: utf-8 -*-
# Manta Python
# Manta Protocol Implementation for Python
# Copyright (C) 2018-2019 Alessandro Viganò

from io import open
import os

from setuptools import setup

from manta import MANTA_VERSION

here_dir = os.path.dirname(__file__)

with open(os.path.join(here_dir, 'requirements.txt')) as req_file:
    requirements = req_file.read().splitlines()

with open(os.path.join(here_dir, 'requirements-tests.txt')) as req_file:
    requirements_tests = req_file.read().splitlines()

with open(os.path.join(here_dir, 'README.rst'), encoding='utf-8') as f:
    README = f.read()


setup(
    name='manta',
    version='1.6.1',
    description="Manta protocol components",
    long_description=README,
    packages=['manta', 'manta.testing'],
    url='https://appiapay.github.io/manta-python',
    license='BSD',
    author='Alessandro Viganò',
    author_email='alvistar@gmail.com',
    install_requires=requirements,
    extras_require={
        'runner':  requirements_tests,
    },
    python_requires='>=3.7',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Topic :: System :: Networking",
        "Topic :: Office/Business :: Financial :: Point-Of-Sale"
        ],
    entry_points={
        'console_scripts': [
            'manta-runner=manta.testing.__main__:main',
            'manta-store=manta.testing.__main__:store_main',
            'manta-payproc=manta.testing.__main__:payproc_main',
            'manta-wallet=manta.testing.__main__:wallet_main',
        ],
    },

)
