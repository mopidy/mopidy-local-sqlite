from __future__ import unicode_literals

import re

from setuptools import find_packages, setup


def get_version(filename):
    with open(filename) as fh:
        metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", fh.read()))
        return metadata['version']


setup(
    name='Mopidy-Local-SQLite',
    version=get_version('mopidy_local_sqlite/__init__.py'),
    url='https://github.com/tkem/mopidy-local-sqlite',
    license='Apache License, Version 2.0',
    author='Thomas Kemmer',
    author_email='tkemmer@computer.org',
    description='Mopidy SQLite local library extension',
    long_description=open('README.rst').read(),
    packages=find_packages(exclude=['tests', 'tests.*']),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'setuptools',
        'Mopidy >= 1.0',
        'Pykka >= 1.1',
        'uritools >= 1.0'
    ],
    entry_points={
        'mopidy.ext': [
            'local-sqlite = mopidy_local_sqlite:Extension',
        ],
    },
    classifiers=[
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Multimedia :: Sound/Audio :: Players',
    ],
)
