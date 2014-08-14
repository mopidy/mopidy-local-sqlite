from __future__ import unicode_literals

import hashlib
import logging
import sqlite3
import os

from mopidy import local
from mopidy.models import Ref, SearchResult
from mopidy.utils import path  # FIXME: inofficial API

from . import Extension
from . import schema

ROOT_URI = b'local:directory'

ROOT_DIRECTORIES = (
    Ref.directory(uri=b'local:album', name='Albums'),
    Ref.directory(uri=b'local:artist', name='Artists'),
    Ref.directory(uri=b'local:track', name='Tracks')
)

logger = logging.getLogger(__name__)


def validate_artist(artist):
    if not artist.name:
        raise ValueError('Empty artist name')
    if artist.uri:
        uri = artist.uri
    elif artist.musicbrainz_id:
        uri = b'local:artist:mbid:%s' % artist.musicbrainz_id
    else:
        uri = b'local:artist:md5:%s' % hashlib.md5(str(artist)).hexdigest()
    return artist.copy(uri=uri)


def validate_album(album):
    if not album.name:
        raise ValueError('Empty album name')
    if album.uri:
        uri = album.uri
    elif album.musicbrainz_id:
        uri = b'local:album:mbid:%s' % album.musicbrainz_id
    else:
        uri = b'local:album:md5:%s' % hashlib.md5(str(album)).hexdigest()
    return album.copy(uri=uri, artists=map(validate_artist, album.artists))


def validate_track(track):
    if not track.uri:
        raise ValueError('Empty track URI')
    if not track.name:
        raise ValueError('Empty track name')  # FIXME: from uri?
    if track.album and track.album.name:
        album = validate_album(track.album)
    else:
        album = None
    return track.copy(
        album=album,
        artists=map(validate_artist, track.artists),
        composers=map(validate_artist, track.composers),
        performers=map(validate_artist, track.performers)
    )


class SQLiteLibrary(local.Library):

    name = 'sqlite'

    _connection = None

    def __init__(self, config):
        ldd = os.path.join(config['local']['data_dir'], b'sqlite')
        self._dbpath = os.path.join(path.get_or_create_dir(ldd), b'library.db')
        self._config = config[Extension.ext_name]

    def _connect(self):
        if not self._connection:
            connection = sqlite3.connect(
                self._dbpath,
                timeout=self._config['timeout'],
                check_same_thread=False,
                factory=schema.Connection
            )
            if self._config['foreign_keys']:
                connection.execute('PRAGMA foreign_keys = ON')
            else:
                connection.execute('PRAGMA foreign_keys = OFF')
            self._connection = connection
        return self._connection

    def _executescript(self, filename):
        path = os.path.join(os.path.dirname(__file__), b'scripts', filename)
        script = open(path).read()
        with self._connect() as connection:
            return connection.executescript(script)

    def load(self):
        with self._connect() as connection:
            version = schema.get_version(connection)
            logger.debug('SQLite database v%s', version)
            if not version:
                logger.info('Creating SQLite database v%s', schema.VERSION)
                self._executescript('create.sql')
                return 0  # initially empty
            while version != schema.VERSION:
                logger.info('Upgrading SQLite database v%s', version)
                self._executescript('upgrade-v%s.sql' % version)
                version = schema.version(connection)
            return schema.count_tracks(connection)

    def lookup(self, uri):
        return schema.get_track(self._connect(), uri)

    def browse(self, uri):
        # FIXME: sanitize!
        if uri == ROOT_URI:
            return ROOT_DIRECTORIES
        elif uri == 'local:artist':
            return schema.browse_artists(self._connect())
        elif uri == 'local:album':
            return schema.browse_album(self._connect())
        elif uri == 'local:track':
            return schema.browse_tracks(self._connect())
        elif uri.startswith('local:album:'):
            return schema.browse_album(self._connect(), uri)
        elif uri.startswith('local:artist:'):
            return schema.browse_artists(self._connect(), uri)
        else:
            logger.error('Invalid browse URI %r', uri)
            return []

    def search(self, query=None, limit=100, offset=0, uris=None, exact=False):
        logger.debug('sqlite: search(%r, %r)', query, uris)
        return SearchResult(tracks=[])

    def begin(self):
        return schema.get_tracks(self._connect())

    def add(self, track):
        try:
            schema.insert_track(self._connect(), validate_track(track))
        except ValueError as e:
            logger.warn('Skipped %s: %s.', track.uri, e)

    def remove(self, uri):
        schema.delete_track(self._connect(), uri)

    def flush(self):
        if not self._connection:
            return False
        self._connection.commit()
        return True

    def close(self):
        schema.cleanup(self._connection)
        self._connection.commit()
        self._connection.close()
        self._connection = None

    def clear(self):
        try:
            with self._connect() as connection:
                schema.clear(connection)
                connection.execute('VACUUM')
                return True
        except sqlite3.Error as e:
            logger.error('SQLite error: %s', e)
            return False
