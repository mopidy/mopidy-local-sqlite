from __future__ import unicode_literals

import hashlib
import logging
import os
import re
import sqlite3
import urllib

from mopidy import local
from mopidy.models import Ref, SearchResult

from . import Extension, schema

_LOCAL_URI_RE = re.compile(r'local:(\w+)(?::(.*))?\Z')

_TRACK_URI_RE = re.compile(r'local:track:(.*/)?([^.]+)(\..*)?\Z')

_ROOT_DIRECTORIES = (
    Ref.directory(uri=b'local:album', name='Albums'),
    Ref.directory(uri=b'local:artist', name='Artists'),
    Ref.directory(uri=b'local:track', name='Tracks')
)

logger = logging.getLogger(__name__)


def _mkdir(*args):
    path = os.path.join(*args)
    if not os.path.isdir(path):
        logger.info('Creating directory %s', path)
        os.makedirs(path, 0755)
    return path


def _mkuri(type, variant, model):
    if variant == 'mbid':
        data = model.musicbrainz_id
    else:
        hash = hashlib.new(variant)
        hash.update(str(model))
        data = hash.hexdigest()
    assert data, 'uri data must not be null'
    return b'local:%s:%s:%s' % (type, variant, data)


class SQLiteLibrary(local.Library):

    name = 'sqlite'

    _connection = None

    def __init__(self, config):
        self._dir = _mkdir(config['local']['data_dir'], b'sqlite')
        self._dbpath = os.path.join(self._dir, b'library.db')
        self._config = config[Extension.ext_name]

    def load(self):
        with self._connect() as connection:
            version = schema.load(connection)
            logger.info('Using SQLite database schema v%s', version)
            return schema.count_tracks(connection)

    def lookup(self, uri):
        return schema.get_track(self._connect(), uri)

    def browse(self, uri):
        try:
            # FIXME: https://github.com/mopidy/mopidy/issues/833
            type, id = _LOCAL_URI_RE.match(uri or 'local:directory').groups()
        except AttributeError:
            logger.error('Invalid local URI %s', uri)
            return []
        if type == 'directory':
            return _ROOT_DIRECTORIES
        elif type == 'album':
            return schema.browse_albums(self._connect(), uri if id else None)
        elif type == 'artist':
            return schema.browse_artists(self._connect(), uri if id else None)
        elif type == 'track' and id is None:
            return schema.browse_tracks(self._connect())
        else:
            logger.error('Invalid browse URI %s', uri)
            return []

    def search(self, query=None, limit=100, offset=0, uris=None, exact=False):
        q = []
        for field, values in (query.items() if query else []):
            if isinstance(values, basestring):
                q.append((field, values))
            else:
                q.extend((field, value) for value in values)
        # TODO: handle `uris`
        tracks = schema.search_tracks(self._connect(), q, limit, offset, exact)
        # TODO: add local:search:<query>
        return SearchResult(uri='local:search', tracks=tracks)

    def begin(self):
        return schema.iter_tracks(self._connect())

    def add(self, track):
        logger.debug('Adding track %r', track)
        try:
            schema.insert_track(self._connect(), self._validate_track(track))
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
                return True
        except sqlite3.Error as e:
            logger.error('SQLite error: %s', e)
            return False

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

    def _validate_artist(self, artist):
        if not artist.name:
            raise ValueError('Empty artist name')
        if artist.uri:
            uri = artist.uri
        elif artist.musicbrainz_id and self._config['use_artist_mbid_uri']:
            uri = _mkuri('artist', 'mbid', artist)
        else:
            uri = _mkuri('artist', self._config['hash'], artist)
        return artist.copy(uri=uri)

    def _validate_album(self, album):
        if not album.name:
            raise ValueError('Empty album name')
        if album.uri:
            uri = album.uri
        elif album.musicbrainz_id and self._config['use_album_mbid_uri']:
            uri = _mkuri('album', 'mbid', album)
        else:
            uri = _mkuri('album', self._config['hash'], album)
        artists = map(self._validate_artist, album.artists)
        return album.copy(uri=uri, artists=artists)

    def _validate_track(self, track):
        if not track.uri:
            raise ValueError('Empty track URI')
        if track.name:
            name = track.name
        else:
            name = urllib.unquote(_TRACK_URI_RE.match(track.uri).group(2))
        if track.album and track.album.name:
            album = self._validate_album(track.album)
        else:
            album = None
        return track.copy(
            name=name,
            album=album,
            artists=map(self._validate_artist, track.artists),
            composers=map(self._validate_artist, track.composers),
            performers=map(self._validate_artist, track.performers)
        )
