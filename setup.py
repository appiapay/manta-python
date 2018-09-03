from distutils.core import setup

setup(
    name='manta',
    version='1.4',
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
