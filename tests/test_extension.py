from __future__ import unicode_literals

import unittest

from mopidy_local_sqlite import Extension


class ExtensionTest(unittest.TestCase):

    def test_get_default_config(self):
        ext = Extension()
        config = ext.get_default_config()
        self.assertIn('[local-sqlite]', config)
        self.assertIn('enabled = true', config)

    def test_get_config_schema(self):
        ext = Extension()
        schema = ext.get_config_schema()
        self.assertIn('hash', schema)
        self.assertIn('use_album_mbid_uri', schema)
        self.assertIn('use_artist_mbid_uri', schema)
        self.assertIn('foreign_keys', schema)
        self.assertIn('timeout', schema)
