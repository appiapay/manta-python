from setuptools import setup
from manta import MANTA_VERSION

setup(
    name='manta',
    version=MANTA_VERSION,
    packages=['manta'],
    url='',
    license='',
    author='Alessandro Viganò',
    author_email='alvistar@gmail.com',
    description='',
    install_requires=[
        "simplejson",
        "cattrs",
        "cryptography",
        "certvalidator",
        "paho-mqtt",
    ]
)
