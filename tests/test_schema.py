from __future__ import unicode_literals

import sqlite3
import unittest

from mopidy.models import Artist, Album, Track
from mopidy_local_sqlite import schema

DBPATH = ':memory:'


class SchemaTest(unittest.TestCase):
    artists = [
        Artist(uri='local:artist:0', name='artist #0'),
        Artist(uri='local:artist:1', name='artist #1'),
    ]
    albums = [
        Album(uri='local:album:0', name='album #0'),
        Album(uri='local:album:1', name='album #1', artists=[artists[0]]),
    ]
    tracks = [
        Track(uri='local:track:0', name='track #0'),
        Track(uri='local:track:1', name='track #1', artists=[artists[0]]),
        Track(uri='local:track:2', name='track #2', album=albums[0]),
        Track(uri='local:track:3', name='track #3', album=albums[1],
              artists=[artists[1]]),
    ]

    def setUp(self):
        self.connection = sqlite3.connect(DBPATH, factory=schema.Connection)
        self.connection.execute('PRAGMA foreign_keys = ON')
        schema.load(self.connection)
        for track in self.tracks:
            schema.insert_track(self.connection, track)
        schema.cleanup(self.connection)

    def tearDown(self):
        self.connection.close()
        self.connection = None

    def test_create(self):
        count = schema.count_tracks(self.connection)
        self.assertEqual(len(self.tracks), count)
        tracks = list(schema.iter_tracks(self.connection))
        self.assertEqual(len(self.tracks), len(tracks))

    def test_lookup(self):
        for track in self.tracks:
            result = schema.get_track(self.connection, track.uri)
            # cannot use result == track here...
            self.assertEqual(track.uri, result.uri)
            self.assertEqual(track.name, result.name)

    def test_indexed_search(self):
        query = [('track_name', self.tracks[0].name)]
        result = schema.search_tracks(self.connection, query, 100, 0, True)
        self.assertEqual(1, len(result))
        self.assertEqual(self.tracks[0].uri, result[0].uri)

        query = [('artist', next(iter(self.tracks[1].artists)).name)]
        result = schema.search_tracks(self.connection, query, 100, 0, True)
        self.assertEqual(1, len(result))
        self.assertEqual(self.tracks[1].uri, result[0].uri)

        query = [('album', self.tracks[2].album.name)]
        result = schema.search_tracks(self.connection, query, 100, 0, True)
        self.assertEqual(1, len(result))
        self.assertEqual(self.tracks[2].uri, result[0].uri)

        query = [('any', self.artists[0].name)]
        result = schema.search_tracks(self.connection, query, 100, 0, True)
        self.assertEqual(2, len(result))

        query = [('track_name', 'track')]
        result = schema.search_tracks(self.connection, query, 100, 0, True)
        self.assertEqual(0, len(result))

    def test_fulltext_search(self):
        query = [('track_name', self.tracks[0].name)]
        result = schema.search_tracks(self.connection, query, 100, 0, False)
        self.assertEqual(1, len(result))
        self.assertEqual(self.tracks[0].uri, result[0].uri)

        query = [('artist', next(iter(self.tracks[1].artists)).name)]
        result = schema.search_tracks(self.connection, query, 100, 0, False)
        self.assertEqual(1, len(result))
        self.assertEqual(self.tracks[1].uri, result[0].uri)

        query = [('album', self.tracks[2].album.name)]
        result = schema.search_tracks(self.connection, query, 100, 0, False)
        self.assertEqual(1, len(result))
        self.assertEqual(self.tracks[2].uri, result[0].uri)

        query = [('any', self.artists[0].name)]
        result = schema.search_tracks(self.connection, query, 100, 0, True)
        self.assertEqual(2, len(result))

        query = [('track_name', 'track')]
        result = schema.search_tracks(self.connection, query, 100, 0, False)
        self.assertEqual(len(self.tracks), len(result))

    def test_browse_artists(self):
        result = schema.browse_artists(self.connection)
        self.assertEqual(len(self.artists), len(result))

        result = schema.browse_artists(self.connection, self.artists[0].uri)
        self.assertEqual(2, len(result))  # one album and one track w/o album

        result = schema.browse_artists(self.connection, self.artists[1].uri)
        self.assertEqual(1, len(result))

    def test_browse_albums(self):
        result = schema.browse_albums(self.connection)
        self.assertEqual(len(self.albums), len(result))

        result = schema.browse_albums(self.connection, self.albums[0].uri)
        self.assertEqual(1, len(result))

    def test_browse_tracks(self):
        result = schema.browse_tracks(self.connection)
        self.assertEqual(len(self.tracks), len(result))
