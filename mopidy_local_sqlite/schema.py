from __future__ import unicode_literals

import itertools
import logging
import operator
import os
import sqlite3

from mopidy.models import Artist, Album, Track, Ref

_BROWSE_FILTERS = {
    None: {
        'album': 'track.album = ?',
        'artist': 'track.artists = ?',
        'composer': 'track.composers = ?',
        'performer': 'track.performers = ?',
        'genre': 'track.genre = ?',
        'date': "track.date LIKE ? || '%'"
    },
    Ref.ARTIST: {
        'artist': """
        EXISTS (SELECT * FROM track WHERE track.artists = artist.uri)
            OR
        EXISTS (SELECT * FROM album WHERE album.artists = artist.uri)
        """,
        'composer': """
        EXISTS (SELECT * FROM track WHERE track.composers = artist.uri)
        """,
        'performer': """
        EXISTS (SELECT * FROM track WHERE track.performers = artist.uri)
        """,
    },
    Ref.ALBUM: {
        'artist': """
        ? IN (
            SELECT artists
             UNION
            SELECT artists FROM track WHERE album = album.uri
        )
        """,
        'composer': """
        ? IN (SELECT composers FROM track WHERE album = album.uri)
        """,
        'performer': """
        ? IN (SELECT performers FROM track WHERE album = album.uri)
        """,
        'genre': """
        ? IN (SELECT genre FROM track WHERE album = album.uri)
        """,
        'date': """
        EXISTS (
            SELECT * FROM track WHERE album = album.uri AND date LIKE ? || '%'
        )
        """
    },
    Ref.TRACK: {
        'album': 'album = ?',
        'artist': """
        ? IN (
            SELECT artists
             UNION
            SELECT artists FROM album WHERE uri = track.album
        )
        """,
        'composer': 'composers = ?',
        'performer': 'performers = ?',
        'genre': 'genre = ?',
        'date': "date LIKE ? || '%'"
    }
}

_BROWSE_SQL = """
SELECT CASE WHEN album.uri IS NULL THEN 'track' ELSE 'album' END AS type,
       coalesce(album.uri, track.uri) AS uri,
       coalesce(album.name, track.name) AS name
  FROM track LEFT OUTER JOIN album ON track.album = album.uri
"""

_BROWSE_ALBUMARTIST_SQL = """
SELECT 'album' AS type, uri AS uri, name AS name
  FROM album
 WHERE album.artists = ?
"""

_SEARCH_FIELDS = {
    'uri',
    'track_name',
    'album',
    'artist',
    'composer',
    'performer',
    'albumartist',
    'genre',
    'track_no',
    'date',
    'comment'
}

_SEARCH_FILTERS = {
    'album': 'album_uri = ?',
    'artist': '? IN (artist_uri, albumartist_uri)',
    'composer': 'composer_uri = ?',
    'performer': 'performer_uri = ?',
    'genre': 'genre = ?',
    'date': "date LIKE ? || '%'"
}

_SEARCH_SQL = """
SELECT *
  FROM tracks
 WHERE docid IN (SELECT docid FROM %s WHERE %s)
"""

_USER_VERSION = 3

logger = logging.getLogger(__name__)


class Connection(sqlite3.Connection):

    class Row(sqlite3.Row):

        def __getattr__(self, name):
            return self[name]

    def __init__(self, *args, **kwargs):
        sqlite3.Connection.__init__(self, *args, **kwargs)
        self.execute('PRAGMA foreign_keys = ON')
        self.row_factory = self.Row

    def executenamed(self, sql, params):
        sql = sql % (', '.join(params.keys()), ', '.join(['?'] * len(params)))
        logger.debug('SQLite statement: %s %r', sql, params.values())
        return self.execute(sql, params.values())


def load(c):
    scripts_dir = os.path.join(os.path.dirname(__file__), b'scripts')
    user_version = c.execute('PRAGMA user_version').fetchone()[0]
    if not user_version:
        logger.info('Creating SQLite database schema v%s', _USER_VERSION)
        script = os.path.join(scripts_dir, 'create-v%s.sql' % _USER_VERSION)
        c.executescript(open(script).read())
        user_version = c.execute('PRAGMA user_version').fetchone()[0]
    while user_version != _USER_VERSION:
        logger.info('Upgrading SQLite database schema v%s', user_version)
        script = os.path.join(scripts_dir, 'upgrade-v%s.sql' % user_version)
        c.executescript(open(script).read())
        user_version = c.execute('PRAGMA user_version').fetchone()[0]
    return user_version


def tracks(c):
    return itertools.imap(_track, c.execute('SELECT * FROM tracks'))


def genres(c):
    return itertools.imap(operator.itemgetter(0), c.execute("""
    SELECT DISTINCT genre
      FROM tracks
     WHERE genre IS NOT NULL
     ORDER BY genre
    """))


def dates(c, format='%Y-%m-%d'):
    return itertools.imap(operator.itemgetter(0), c.execute("""
    SELECT DISTINCT strftime(?, date) AS date
      FROM tracks
     WHERE date IS NOT NULL
     ORDER BY date
    """, [format]))


def images(c):
    for row in c.execute('SELECT images FROM album WHERE images IS NOT NULL'):
        for image in row[0].split():
            yield image


def lookup(c, uri):
    row = c.execute('SELECT * FROM tracks WHERE uri = ?', [uri]).fetchone()
    if row:
        return _track(row)
    else:
        return None


def browse(c, type=None, order=('type', 'name'), **kwargs):
    if type:
        sql = "SELECT '%s' AS type, uri, name FROM %s" % (type, type)
    else:
        sql = _BROWSE_SQL
    filters, params = _make_filters(_BROWSE_FILTERS[type], **kwargs)
    if filters:
        sql += ' WHERE %s' % ' AND '.join(filters)
    if not type:
        sql += ' GROUP BY coalesce(album.uri, track.uri)'
        # as of sqlite v3.8.2, a UNION seems to be considerably faster
        # than a WHERE clause spanning multiple tables in a JOIN
        if 'artist' in kwargs:
            sql = ' UNION '.join((sql, _BROWSE_ALBUMARTIST_SQL))
            params.append(kwargs['artist'])
    if order:
        sql += ' ORDER BY %s' % ', '.join(order)
    logger.debug('SQLite query: %s %r', sql, params)
    return itertools.imap(_ref, c.execute(sql, params))  # imap?


def search_tracks(c, query, limit, offset, exact, **kwargs):
    if not query:
        sql, params = ('SELECT * FROM tracks', [])
    elif exact:
        sql, params = _make_indexed_query(query)
    else:
        sql, params = _make_fulltext_query(query)
    if kwargs:
        filters, fparams = _make_filters(_SEARCH_FILTERS, **kwargs)
        sql = 'SELECT * FROM (%s) WHERE %s' % (sql, ' AND '.join(filters))
        params.extend(fparams)
    logger.debug('SQLite query: %s %r', sql, params)
    rows = c.execute(sql + ' LIMIT ? OFFSET ?', params + [limit, offset])
    return map(_track, rows)


def insert_artists(c, artists):
    if not artists:
        return None
    if len(artists) != 1:
        logger.warn('Ignoring multiple artists: %r', artists)
    artist = next(iter(artists))
    c.executenamed('INSERT OR REPLACE INTO artist (%s) VALUES (%s)', {
        'uri': artist.uri,
        'name': artist.name,
        'musicbrainz_id': artist.musicbrainz_id
    })
    return artist.uri


def insert_album(c, album):
    if not album or not album.name:
        return None
    c.executenamed('INSERT OR REPLACE INTO album (%s) VALUES (%s)', {
        'uri': album.uri,
        'name': album.name,
        'artists': insert_artists(c, album.artists),
        'num_tracks': album.num_tracks,
        'num_discs': album.num_discs,
        'date': album.date,
        'musicbrainz_id': album.musicbrainz_id,
        'images': ' '.join(album.images) if album.images else None
    })
    return album.uri


def insert_track(c, track):
    c.executenamed('INSERT OR REPLACE INTO track (%s) VALUES (%s)', {
        'uri': track.uri,
        'name': track.name,
        'album': insert_album(c, track.album),
        'artists': insert_artists(c, track.artists),
        'composers': insert_artists(c, track.composers),
        'performers': insert_artists(c, track.performers),
        'genre': track.genre,
        'track_no': track.track_no,
        'disc_no': track.disc_no,
        'date': track.date,
        'length': track.length,
        'bitrate': track.bitrate,
        'comment': track.comment,
        'musicbrainz_id': track.musicbrainz_id,
        'last_modified': track.last_modified
    })
    return track.uri


def delete_track(c, uri):
    c.execute('DELETE FROM track WHERE uri = ?', (uri,))


def count_tracks(c):
    return c.execute('SELECT count(*) FROM track').fetchone()[0]


def cleanup(c):
    c.execute("""
    DELETE FROM album WHERE NOT EXISTS (
        SELECT uri FROM track WHERE track.album = album.uri
    )
    """)
    c.execute("""
    DELETE FROM artist WHERE NOT EXISTS (
        SELECT uri FROM track WHERE track.artists = artist.uri
         UNION
        SELECT uri FROM track WHERE track.composers = artist.uri
         UNION
        SELECT uri FROM track WHERE track.performers = artist.uri
         UNION
        SELECT uri FROM album WHERE album.artists = artist.uri
    )
    """)
    c.execute('ANALYZE')


def clear(c):
    c.executescript("""
    DELETE FROM track;
    DELETE FROM album;
    DELETE FROM artist;
    VACUUM;
    """)


def _make_filters(mapping, role=None, **kwargs):
    filters, params = [], []
    if role:
        filters.append(mapping[role])
    for key, value in kwargs.items():
        filters.append(mapping[key])
        params.append(value)
    return (filters, params)


def _make_indexed_query(query):
    terms = []
    params = []
    for field, value in query:
        if field == 'any':
            terms.append('? IN (%s)' % ','.join(_SEARCH_FIELDS))
        elif field in _SEARCH_FIELDS:
            terms.append('%s = ?' % field)
        else:
            raise LookupError('Invalid search field: %s' % field)
        params.append(value)
    return (_SEARCH_SQL % ('search', ' AND '.join(terms)), params)


def _make_fulltext_query(query):
    terms = []
    params = []
    for field, value in query:
        if field == 'any':
            terms.append(_SEARCH_SQL % ('fts', 'fts MATCH ?'))
        elif field in _SEARCH_FIELDS:
            terms.append(_SEARCH_SQL % ('fts', '%s MATCH ?' % field))
        else:
            raise LookupError('Invalid search field: %s' % field)
        params.append(value)
    return (' INTERSECT '.join(terms), params)


def _track(row):
    kwargs = {
        'uri': row.uri,
        'name': row.name,
        'genre': row.genre,
        'track_no': row.track_no,
        'disc_no': row.disc_no,
        'date': row.date,
        'length': row.length,
        'bitrate': row.bitrate,
        'comment': row.comment,
        'musicbrainz_id': row.musicbrainz_id,
        'last_modified': row.last_modified
    }
    if row.album_uri is not None:
        if row.albumartist_uri is not None:
            albumartists = [Artist(
                uri=row.albumartist_uri,
                name=row.albumartist_name,
                musicbrainz_id=row.albumartist_musicbrainz_id
            )]
        else:
            albumartists = None
        kwargs['album'] = Album(
            uri=row.album_uri,
            name=row.album_name,
            artists=albumartists,
            num_tracks=row.album_num_tracks,
            num_discs=row.album_num_discs,
            date=row.album_date,
            musicbrainz_id=row.album_musicbrainz_id,
            images=row.album_images.split() if row.album_images else None
        )
    if row.artist_uri is not None:
        kwargs['artists'] = [Artist(
            uri=row.artist_uri,
            name=row.artist_name,
            musicbrainz_id=row.artist_musicbrainz_id
        )]
    if row.composer_uri is not None:
        kwargs['composers'] = [Artist(
            uri=row.composer_uri,
            name=row.composer_name,
            musicbrainz_id=row.composer_musicbrainz_id
        )]
    if row.performer_uri is not None:
        kwargs['performers'] = [Artist(
            uri=row.performer_uri,
            name=row.performer_name,
            musicbrainz_id=row.performer_musicbrainz_id
        )]
    return Track(**kwargs)


def _ref(row):
    return Ref(type=row.type, uri=row.uri, name=row.name)
