from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='notmuch-lazysync',
    version='0.1a',
    description='A tool for notmuch tag synchronization',
    url='https://github.com/dschoepe/notmuch-lazysync',
    author='Daniel Schoepe',
    author_email='daniel@schoepe.org',
    license='GPLv2+',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Communications :: Email',
        'Topic :: Communications :: Email :: Email Clients (MUA)',
        'Topic :: Utilities',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    keywords='synchronization notmuch',
    packages=["notmuch_lazysync"],
    entry_points={
        'console_scripts': [
            'notmuch-lazysync=notmuch_lazysync.lazysync:main',
        ],
    },
)
