from __future__ import unicode_literals

import sqlite3
import unittest

from mopidy.models import Ref, Artist, Album, Track
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
        Album(uri='local:album:2', name='album #2', artists=[artists[1]])
    ]
    tracks = [
        Track(uri='local:track:0', name='track #0'),
        Track(uri='local:track:1', name='track #1', artists=[artists[0]]),
        Track(uri='local:track:2', name='track #2', album=albums[0]),
        Track(uri='local:track:3', name='track #3', album=albums[1]),
        Track(uri='local:track:4', name='track #4', album=albums[2],
              composers=[artists[0]], performers=[artists[0]])
    ]

    def setUp(self):
        self.connection = sqlite3.connect(DBPATH, factory=schema.Connection)
        schema.load(self.connection)
        for track in self.tracks:
            schema.insert_track(self.connection, track)

    def tearDown(self):
        self.connection.close()
        self.connection = None

    def test_create(self):
        count = schema.count_tracks(self.connection)
        self.assertEqual(len(self.tracks), count)
        tracks = list(schema.tracks(self.connection))
        self.assertEqual(len(self.tracks), len(tracks))

    def test_lookup(self):
        for track in self.tracks:
            result = schema.lookup(self.connection, track.uri)
            # cannot use result == track here...
            self.assertEqual(track.uri, result.uri)
            self.assertEqual(track.name, result.name)

    def test_indexed_search(self):
        for results, query, filters in [
            (
                map(lambda t: t.uri, self.tracks),
                [],
                {}
            ),
            (
                [],
                [('any', 'none')],
                {}
            ),
            (
                [self.tracks[1].uri, self.tracks[3].uri, self.tracks[4].uri],
                [('any', self.artists[0].name)],
                {}
            ),
            (
                [self.tracks[3].uri],
                [('any', self.artists[0].name)],
                {'album': self.albums[1].uri},
            ),
            (
                [self.tracks[2].uri],
                [('album', self.tracks[2].album.name)],
                {},
            ),
            (
                [self.tracks[1].uri],
                [('artist', next(iter(self.tracks[1].artists)).name)],
                {},
            ),
            (
                [self.tracks[0].uri],
                [('track_name', self.tracks[0].name)],
                {}
            ),
        ]:
            for exact in (True, False):
                with self.connection as c:
                    tracks = schema.search_tracks(c, query, 10, 0, exact, **filters)  # noqa
                self.assertItemsEqual(results, map(lambda t: t.uri, tracks))

    def test_fulltext_search(self):
        for results, query, filters in [
            (
                map(lambda t: t.uri, self.tracks),
                [('track_name', 'track')],
                {}
            ),
            (
                [self.tracks[1].uri, self.tracks[3].uri],
                [('track_name', 'track')],
                {'artist': self.artists[0].uri}
            ),
        ]:
            with self.connection as c:
                tracks = schema.search_tracks(c, query, 10, 0, False, **filters)  # noqa
            self.assertItemsEqual(results, map(lambda t: t.uri, tracks))

    def test_browse_artists(self):
        with self.connection as c:
            result = list(schema.browse(c, Ref.ARTIST))
            self.assertEqual(len(self.artists), len(result))

            result = list(schema.browse(c, Ref.ARTIST, role='artist'))
            self.assertEqual(2, len(result))

            result = list(schema.browse(c, Ref.ARTIST, role='composer'))
            self.assertEqual(1, len(result))

            result = list(schema.browse(c, Ref.ARTIST, role='performer'))
            self.assertEqual(1, len(result))

    def test_browse_albums(self):
        with self.connection as c:
            result = schema.browse(c, Ref.ALBUM)
            result = list(result)
            self.assertEqual(len(self.albums), len(result))

            result = schema.browse(c, Ref.ALBUM, artist=self.artists[0].uri)
            result = list(result)
            self.assertEqual(1, len(result))

    def test_browse_tracks(self):
        with self.connection as c:
            result = schema.browse(c, Ref.TRACK)
            result = list(result)
            self.assertEqual(len(self.tracks), len(result))

            result = schema.browse(c, Ref.TRACK, artist=self.artists[0].uri)
            result = list(result)
            self.assertEqual(2, len(result))

            result = schema.browse(c, Ref.TRACK, artist=self.artists[1].uri)
            result = list(result)
            self.assertEqual(1, len(result))

            result = schema.browse(c, Ref.TRACK, composer=self.artists[0].uri)
            result = list(result)
            self.assertEqual(1, len(result))

            result = schema.browse(c, Ref.TRACK, performer=self.artists[0].uri)
            result = list(result)
            self.assertEqual(1, len(result))

    def test_delete(self):
        c = self.connection
        schema.delete_track(c, self.tracks[0].uri)
        schema.cleanup(c)
        self.assertEqual(3, len(c.execute('SELECT * FROM album').fetchall()))
        self.assertEqual(2, len(c.execute('SELECT * FROM artist').fetchall()))

        schema.delete_track(c, self.tracks[1].uri)
        schema.cleanup(c)
        self.assertEqual(3, len(c.execute('SELECT * FROM album').fetchall()))
        self.assertEqual(2, len(c.execute('SELECT * FROM artist').fetchall()))

        schema.delete_track(c, self.tracks[2].uri)
        schema.cleanup(c)
        self.assertEqual(2, len(c.execute('SELECT * FROM album').fetchall()))
        self.assertEqual(2, len(c.execute('SELECT * FROM artist').fetchall()))

        schema.delete_track(c, self.tracks[3].uri)
        schema.cleanup(c)
        self.assertEqual(1, len(c.execute('SELECT * FROM album').fetchall()))
        self.assertEqual(2, len(c.execute('SELECT * FROM artist').fetchall()))

        schema.delete_track(c, self.tracks[4].uri)
        schema.cleanup(c)
        self.assertEqual(0, len(c.execute('SELECT * FROM album').fetchall()))
        self.assertEqual(0, len(c.execute('SELECT * FROM artist').fetchall()))
