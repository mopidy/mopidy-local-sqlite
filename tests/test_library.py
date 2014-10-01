from __future__ import unicode_literals

import shutil
import tempfile
import unittest
import urllib

from mopidy.models import Track
from mopidy_local_sqlite import library


class LocalLibraryProviderTest(unittest.TestCase):

    config = {
        'local-sqlite': {
            'directories': [],
            'encodings': ['utf-8', 'latin-1'],
            'timeout': 1.0,
            'use_album_mbid_uri': False,
            'use_artist_mbid_uri': False,
            'extract_images': False
        }
    }

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.library = library.SQLiteLibrary(dict(self.config, local={
            'media_dir': self.tempdir,
            'data_dir': self.tempdir
        }))
        self.library.load()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_add_noname_utf8(self):
        name = u'Adresse d\xe9j\xe0 utilis\xe9e'
        uri = 'local:track:%s.mp3' % urllib.quote(name.encode('utf8'))
        self.library.begin()
        self.library.add(Track(uri=uri))
        self.library.close()
        self.assertEqual(self.library.lookup(uri).name, name)

    def test_add_noname_latin1(self):
        name = u'Adresse d\xe9j\xe0 utilis\xe9e'
        uri = 'local:track:%s.mp3' % urllib.quote(name.encode('latin1'))
        self.library.begin()
        self.library.add(Track(uri=uri))
        self.library.close()
        self.assertEqual(self.library.lookup(uri).name, name)

    def test_clear(self):
        self.library.begin()
        self.library.add(Track(uri='local:track:track.mp3'))
        self.library.close()
        self.library.clear()
        self.assertEqual(self.library.load(), 0)
