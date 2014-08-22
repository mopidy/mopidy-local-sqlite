from __future__ import unicode_literals

import itertools
import logging
import os
import sqlite3

from mopidy.models import Artist, Album, Track, Ref

logger = logging.getLogger(__name__)

USER_VERSION = 2

_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), b'scripts')

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

_SEARCH_SQL = """
SELECT *
  FROM tracks
 WHERE docid IN (SELECT docid FROM %s WHERE %s)
"""


def _sqlstr(fmt, *args):
    return fmt % tuple(', '.join(['?'] * n) for n in args)


def _ref(row):
    return Ref(type=row.type, uri=row.uri, name=row.name)


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


def _build_search_query(query):
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


def _build_fts_query(query):
    terms = []
    params = []
    for field, value in query:
        if field == 'any':
            terms.append(_SEARCH_SQL % ('fts', 'fts MATCH ?'))
        elif field in _SEARCH_FIELDS:
            terms.append(_SEARCH_SQL % ('fts', '%s MATCH ?' % field))
        else:
            raise LookupError('Invalid search field: %s' % field)
        params.append(value)  # TODO: escaping?
    return (' INTERSECT '.join(terms), params)


def _executescript(c, filename):
    path = os.path.join(_SCRIPTS_DIR, filename)
    script = open(path).read()
    return c.executescript(script)


def load(c):
    user_version = c.execute('PRAGMA user_version').fetchone()[0]
    if not user_version:
        logger.info('Creating SQLite database schema v%s', USER_VERSION)
        _executescript(c, 'create-v%s.sql' % USER_VERSION)
        user_version = c.execute('PRAGMA user_version').fetchone()[0]
    while user_version != USER_VERSION:
        logger.info('Upgrading SQLite database schema v%s', user_version)
        _executescript(c, 'upgrade-v%s.sql' % user_version)
        user_version = c.execute('PRAGMA user_version').fetchone()[0]
    return user_version


def count_tracks(c):
    return c.execute('SELECT count(*) FROM track').fetchone()[0]


def iter_tracks(c):
    return itertools.imap(_track, c.execute('SELECT * FROM tracks'))


def iter_images(c):
    for row in c.execute('SELECT images FROM album WHERE images IS NOT NULL'):
        for image in row[0].split():
            yield image


def get_track(c, uri):
    row = c.execute('SELECT * FROM tracks WHERE uri = ?', [uri]).fetchone()
    if row:
        return _track(row)
    else:
        return None


def browse_albums(c, uri=None):
    if uri is None:
        sql = """
        SELECT 'directory' AS type, uri, name
          FROM album
         ORDER BY name
        """
    else:
        sql = """
        SELECT 'track' AS type, uri, name
          FROM track
         WHERE album = :uri
         ORDER BY disc_no, track_no, name
        """
    return map(_ref, c.execute(sql, {'uri': uri}))


def browse_artists(c, uri=None):
    if uri is None:
        sql = """
        SELECT 'directory' AS type, uri, name
          FROM artist
         WHERE EXISTS (SELECT * FROM album WHERE album.artists = artist.uri)
            OR EXISTS (SELECT * FROM track WHERE track.artists = artist.uri)
         ORDER BY name
        """
    else:
        sql = """
        SELECT 'directory' AS type, uri, name
          FROM album
         WHERE artists = :uri
         UNION
        SELECT 'track', track.uri, track.name
          FROM track
          LEFT OUTER JOIN album ON track.album = album.uri
         WHERE track.artists = :uri
           AND (album.artists IS NULL OR album.artists != :uri)
         ORDER BY type, name
        """
    return map(_ref, c.execute(sql, {'uri': uri}))


def browse_tracks(c):
    sql = """
    SELECT 'track' AS type, uri, name
      FROM track
     ORDER BY name
    """
    return map(_ref, c.execute(sql))


def search_tracks(c, query, limit, offset, exact):
    if exact:
        sql, params = _build_search_query(query)
    else:
        sql, params = _build_fts_query(query)
    logger.debug('SQL query: %s (%s)', sql, ','.join(params))
    result = c.execute(sql + ' LIMIT ? OFFSET ?', params + [limit, offset])
    logger.debug('SQL query result: %r', result)
    return map(_track, result)


def insert_artists(c, artists):
    if not artists:
        return None
    if len(artists) != 1:
        logger.warn('Ignoring multiple artists: %r', artists)
    artist = list(artists)[0]
    c.execute(_sqlstr('INSERT OR REPLACE INTO artist VALUES (%s)', 3), (
        artist.uri,
        artist.name,
        artist.musicbrainz_id
        ))
    return artist.uri


def insert_album(c, album):
    if not album or not album.name:
        return None
    c.execute(_sqlstr('INSERT OR REPLACE INTO album VALUES (%s)', 8), (
        album.uri,
        album.name,
        insert_artists(c, album.artists),
        album.num_tracks,
        album.num_discs,
        album.date,
        album.musicbrainz_id,
        ' '.join(album.images) if album.images else None
        ))
    return album.uri


def insert_track(c, track):
    c.execute(_sqlstr('INSERT OR REPLACE INTO track VALUES (%s)', 15), (
        track.uri,
        track.name,
        insert_album(c, track.album),
        insert_artists(c, track.artists),
        insert_artists(c, track.composers),
        insert_artists(c, track.performers),
        track.genre,
        track.track_no,
        track.disc_no,
        track.date,
        track.length,
        track.bitrate,
        track.comment,
        track.musicbrainz_id,
        track.last_modified
        ))
    return track.uri


def delete_track(c, uri):
    c.execute('DELETE FROM track WHERE uri = ?', (uri,))


def cleanup(c):
    c.executescript("""
    DELETE FROM album WHERE NOT EXISTS (
        SELECT uri FROM track WHERE track.album = album.uri
    );
    DELETE FROM artist WHERE NOT EXISTS (
        SELECT uri FROM track WHERE track.artists = artist.uri
         UNION
        SELECT uri FROM track WHERE track.composers = artist.uri
         UNION
        SELECT uri FROM track WHERE track.performers = artist.uri
         UNION
        SELECT uri FROM album WHERE album.artists = artist.uri
    );
    """)


def clear(c):
    c.executescript("""
    DELETE FROM track;
    DELETE FROM album;
    DELETE FROM artist;
    VACUUM;
    """)


class Row(sqlite3.Row):

    def __getattr__(self, name):
        return self[name]


class Connection(sqlite3.Connection):

    def __init__(self, *args, **kwargs):
        logger.debug('Creating SQLite connection')
        sqlite3.Connection.__init__(self, *args, **kwargs)
        self.row_factory = Row
