from __future__ import unicode_literals

import itertools
import logging
import sqlite3

from mopidy.models import Artist, Album, Track, Ref

logger = logging.getLogger(__name__)

_ARTIST_COLUMNS = (
    'uri',
    'name',
    'musicbrainz_id'
)

_ALBUM_COLUMNS = (
    'uri',
    'name',
    'artists',
    'num_tracks',
    'num_discs',
    'date',
    'musicbrainz_id'
)

_TRACK_COLUMNS = (
    'uri',
    'name',
    'album',
    'artists',
    'composers',
    'performers',
    'genre',
    'track_no',
    'disc_no',
    'date',
    'length',
    'bitrate',
    'comment',
    'musicbrainz_id',
    'last_modified'
    )

_INSERT_ARTIST_SQL = 'INSERT OR REPLACE INTO artist (%s) VALUES (%s)' % (
    ','.join(_ARTIST_COLUMNS),
    ','.join(':' + name for name in _ARTIST_COLUMNS)
)

_INSERT_ALBUM_SQL = 'INSERT OR REPLACE INTO album (%s) VALUES (%s)' % (
    ','.join(_ALBUM_COLUMNS),
    ','.join(':' + name for name in _ALBUM_COLUMNS)
)

_INSERT_TRACK_SQL = 'INSERT INTO track (%s) VALUES (%s)' % (
    ','.join(_TRACK_COLUMNS),
    ','.join(':' + name for name in _TRACK_COLUMNS)
)

_SELECT_TRACK_SQL = """
SELECT %s, %s, %s, %s, %s, %s
  FROM track
  LEFT OUTER JOIN artist ON track.artists = artist.uri
  LEFT OUTER JOIN artist AS composer ON track.composers = composer.uri
  LEFT OUTER JOIN artist AS performer ON track.performers = performer.uri
  LEFT OUTER JOIN album ON track.album = album.uri
  LEFT OUTER JOIN artist AS albumartist ON album.artists = albumartist.uri
""" % (
    ','.join('track.' + name for name in _TRACK_COLUMNS),
    ','.join('artist.' + name for name in _ARTIST_COLUMNS),
    ','.join('composer.' + name for name in _ARTIST_COLUMNS),
    ','.join('performer.' + name for name in _ARTIST_COLUMNS),
    ','.join('album.' + name for name in _ALBUM_COLUMNS),
    ','.join('albumartist.' + name for name in _ARTIST_COLUMNS)
)

_LOOKUP_TRACK_SQL = _SELECT_TRACK_SQL + 'WHERE track.uri = ?'

_TRACK_INDEX = 0
_ARTISTS_INDEX = _TRACK_INDEX + len(_TRACK_COLUMNS)
_COMPOSERS_INDEX = _ARTISTS_INDEX + len(_ARTIST_COLUMNS)
_PERFORMERS_INDEX = _COMPOSERS_INDEX + len(_ARTIST_COLUMNS)
_ALBUM_INDEX = _PERFORMERS_INDEX + len(_ARTIST_COLUMNS)

VERSION = 1  # SQLite user_version


def _artists_to_uri(artists):
    return set(artists).pop().uri if artists else None


def _artist_to_params(artist):
    return {
        'uri': artist.uri,
        'name': artist.name,
        'musicbrainz_id': artist.musicbrainz_id
    }


def _album_to_params(album):
    if len(album.artists) > 1:
        logger.warn('Ignoring multiple artists for %s', album.uri)
    return {
        'uri': album.uri,
        'name': album.name,
        'artists': _artists_to_uri(album.artists),
        'num_tracks': album.num_tracks,
        'num_discs': album.num_discs,
        'date': album.date,
        'musicbrainz_id': album.musicbrainz_id
    }


def _track_to_params(track):
    if len(track.artists) > 1:
        logger.warn('Ignoring multiple artists for %s', track.uri)
    if len(track.composers) > 1:
        logger.warn('Ignoring multiple composers for %s', track.uri)
    if len(track.performers) > 1:
        logger.warn('Ignoring multiple performers for %s', track.uri)
    return {
        'uri': track.uri,
        'name': track.name,
        'album': track.album.uri if track.album else None,
        'artists': _artists_to_uri(track.artists),
        'composers': _artists_to_uri(track.composers),
        'performers': _artists_to_uri(track.performers),
        'genre': track.genre,
        'track_no': track.track_no,
        'disc_no': track.disc_no,
        'date': track.date,
        'length': track.length,
        'bitrate': track.bitrate,
        'comment': track.comment,
        'musicbrainz_id': track.musicbrainz_id,
        'last_modified': track.last_modified
    }


def _row_to_ref(row):
    type, uri, name = row
    if name:
        return Ref(type=type, uri=uri, name=name)
    else:
        return Ref(type=type, uri=uri, name=uri)


def _row_to_artists(row):
    return [Artist(**dict(zip(_ARTIST_COLUMNS, row)))]


def _row_to_album(row):
    kwargs = dict(zip(_ALBUM_COLUMNS, row))
    if kwargs['artists'] is not None:
        kwargs['artists'] = _row_to_artists(row[len(_ALBUM_COLUMNS):])
    return Album(**kwargs)


def _row_to_track(row):
    kwargs = dict(zip(_TRACK_COLUMNS, row[_TRACK_INDEX:]))
    if kwargs['artists'] is not None:
        kwargs['artists'] = _row_to_artists(row[_ARTISTS_INDEX:])
    if kwargs['composers'] is not None:
        kwargs['composers'] = _row_to_artists(row[_COMPOSERS_INDEX:])
    if kwargs['performers'] is not None:
        kwargs['performers'] = _row_to_artists(row[_PERFORMERS_INDEX:])
    if kwargs['album'] is not None:
        kwargs['album'] = _row_to_album(row[_ALBUM_INDEX:])
    return Track(**kwargs)


def get_version(c):
    return c.execute('PRAGMA user_version').fetchone()[0]


def get_tracks(c):
    return map(_row_to_track, c.execute(_SELECT_TRACK_SQL))


def count_tracks(c):
    return c.execute('SELECT count(*) FROM track').fetchone()[0]


def browse_artists(c, uri=None):
    if uri is None:
        # FIXME: this is slow...
        query = """
        SELECT 'directory', uri, name
          FROM artist
         WHERE EXISTS (SELECT * FROM album WHERE album.artists = artist.uri)
            OR EXISTS (SELECT * FROM track WHERE track.artists = artist.uri)
         ORDER BY name
        """
    else:
        query = """
        SELECT 'directory', uri, name
          FROM album
         WHERE artists = :uri
         UNION
        SELECT 'track', track.uri, track.name
          FROM track
          LEFT OUTER JOIN album ON track.album = album.uri
         WHERE track.artists = :uri AND track.artists != album.artists
         ORDER BY name
        """
    refs = []
    for type, uri, name in c.execute(query,  dict(uri=uri)):
        refs.append(Ref(type=type, uri=uri, name=name))
    return refs


def browse_album(c, uri=None):
    if uri is None:
        query = """
        SELECT 'directory', uri, name
          FROM album
         ORDER BY name
        """
    else:
        query = """
        SELECT 'track', uri, name
          FROM track
         WHERE album = :uri
         ORDER BY disc_no, track_no, name
        """
    refs = []
    for type, uri, name in c.execute(query,  dict(uri=uri)):
        refs.append(Ref(type=type, uri=uri, name=name))
    return refs


def browse_tracks(c):
    refs = []
    for uri, name in c.execute('SELECT uri, name FROM track ORDER BY name'):
        refs.append(Ref.track(uri=uri, name=name))
    return refs


def get_track(c, uri):
    row = c.execute(_LOOKUP_TRACK_SQL, (uri,)).fetchone()
    logger.debug('lookup(%r) -> %r', uri, row)
    return _row_to_track(row)


def insert_track(c, track):
    for artist in itertools.chain(track.artists, track.composers, track.performers):  # noqa
        c.execute(_INSERT_ARTIST_SQL, _artist_to_params(artist))
    if track.album:
        for artist in track.album.artists:
            c.execute(_INSERT_ARTIST_SQL, _artist_to_params(artist))
        c.execute(_INSERT_ALBUM_SQL, _album_to_params(track.album))
    c.execute(_INSERT_TRACK_SQL, _track_to_params(track))


def delete_track(c, uri):
    c.execute('DELETE FROM track WHERE uri = ?', (uri,))


def cleanup(c):
    c.executescript("""
    DELETE FROM album WHERE NOT EXISTS (
        SELECT rowid FROM track WHERE track.album = album.uri
    );
    DELETE FROM artist WHERE NOT EXISTS (
        SELECT rowid FROM track WHERE track.artists = artist.uri
         UNION
        SELECT rowid FROM track WHERE track.composers = artist.uri
         UNION
        SELECT rowid FROM track WHERE track.performers = artist.uri
         UNION
        SELECT rowid FROM album WHERE album.artists = artist.uri
    );
    """)


def clear(c):
    c.executescript("""
    DELETE FROM track;
    DELETE FROM album;
    DELETE FROM artist;
    """)


class Connection(sqlite3.Connection):

    def __init__(self, *args, **kwargs):
        logger.debug('Creating custom SQLite connection')
        sqlite3.Connection.__init__(self, *args, **kwargs)
        # TODO: create custom functions, if any...
