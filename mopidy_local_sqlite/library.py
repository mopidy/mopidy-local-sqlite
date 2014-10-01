from __future__ import unicode_literals

import hashlib
import logging
import os
import re
import sqlite3
import uritools

from mopidy import local
from mopidy.models import Ref, SearchResult

from . import Extension, schema

_BROWSE_TYPES = {
    'track': lambda c, q: schema.browse(c, Ref.TRACK),
    'album': lambda c, q: schema.browse(c, Ref.ALBUM),
    'artist': lambda c, q: [
        ref.copy(type=Ref.DIRECTORY, uri=ref.uri+'?role='+q['role'][0])
        for ref in schema.browse(c, Ref.ARTIST, role=q['role'][0])
    ],
    'genre': lambda c, q: [
        Ref.directory(uri='local:genre:'+uritools.uriencode(genre), name=genre)
        for genre in schema.genres(c)
    ],
    'date': lambda c, q: [
        Ref.directory(uri='local:date:'+date, name=date)
        for date in schema.dates(c, format=q['format'][0])
    ]
}

_TRACK_URI_RE = re.compile(r'local:track:(.*/)?([^.]+)(\..*)?\Z')

logger = logging.getLogger(__name__)


class SQLiteLibrary(local.Library):

    name = 'sqlite'

    def __init__(self, config):
        data_dir = Extension.make_data_dir(config)
        self._config = ext_config = config[Extension.ext_name]
        self._dbpath = os.path.join(data_dir, b'library.db')
        self._connection = None
        self._directories = []
        for line in ext_config['directories']:
            name, uri = line.rsplit(None, 2)
            ref = Ref.directory(uri=uri, name=name)
            self._directories.append(ref)
        if ext_config['extract_images']:
            from .images import ImageDirectory
            self._images = ImageDirectory(config)
        else:
            self._images = None

    def load(self):
        with self._connect() as connection:
            version = schema.load(connection)
            logger.info('Using SQLite database schema v%s', version)
            return schema.count_tracks(connection)

    def lookup(self, uri):
        return schema.lookup(self._connect(), uri)

    def browse(self, uri):
        try:
            if uri == self.ROOT_DIRECTORY_URI:
                return self._directories
            elif uri.startswith('local:directory'):
                return self._browse_directory(uri)
            elif uri.startswith('local:album'):
                return self._browse_album(uri)
            elif uri.startswith('local:artist'):
                return self._browse_artist(uri)
            elif uri.startswith('local:genre'):
                return self._browse_genre(uri)
            elif uri.startswith('local:date'):
                return self._browse_date(uri)
            else:
                raise ValueError('Invalid browse URI')
        except Exception as e:
            logger.error('Error browsing %s: %s', uri, e)
        return []

    def search(self, query=None, limit=100, offset=0, uris=None, exact=False):
        try:
            q = []
            for field, values in (query.items() if query else []):
                if isinstance(values, basestring):
                    q.append((field, values))
                else:
                    q.extend((field, value) for value in values)
            filters = _search_filters_from_uris(uris or [])
            c = self._connect()
            tracks = schema.search_tracks(c, q, limit, offset, exact, filters)
            uri = uritools.uricompose('local', path='search', query=q)
            return SearchResult(uri=uri, tracks=tracks)
        except Exception as e:
            logger.error('Error searching %s: %s', Extension.dist_name, e)
        return None

    def begin(self):
        return schema.tracks(self._connect())

    def add(self, track):
        try:
            track = self._validate_track(track)
            if self._images:
                track = self._images.add(track)
            schema.insert_track(self._connect(), track)
        except Exception as e:
            logger.warn('Skipped %s: %s', track.uri, e)

    def remove(self, uri):
        schema.delete_track(self._connect(), uri)

    def flush(self):
        if not self._connection:
            return False
        self._connection.commit()
        return True

    def close(self):
        schema.cleanup(self._connection)
        if self._images:
            self._images.cleanup(schema.images(self._connection))
        self._connection.commit()
        self._connection.close()
        self._connection = None

    def clear(self):
        with self._connect() as connection:
            try:
                schema.clear(connection)
            except sqlite3.Error as e:
                logger.error('Error clearing SQLite database: %s', e)
                return False
        if self._images:
            try:
                self._images.clear()
            except Exception as e:
                logger.error('Error clearing image directory: %s', e)
                return False
        return True

    def _connect(self):
        if not self._connection:
            self._connection = sqlite3.connect(
                self._dbpath,
                factory=schema.Connection,
                timeout=self._config['timeout'],
                check_same_thread=False,
            )
        return self._connection

    def _browse(self, **kwargs):
        connection = self._connect()
        query = '&'.join('='.join(item) for item in kwargs.items())
        albums = [
            ref.copy(uri=ref.uri+'?'+query)
            for ref in schema.browse(connection, Ref.ALBUM, **kwargs)
        ]
        tracks = schema.browse(connection, Ref.TRACK, album=None, **kwargs)
        return albums + tracks

    def _browse_directory(self, uri):
        query = uritools.urisplit(uri).getquerydict()
        return _BROWSE_TYPES[query['type'][0]](self._connect(), query)

    def _browse_album(self, uri, order=('disc_no', 'track_no', 'name')):
        parts = uritools.urisplit(uri)
        kwargs = {'album': 'local:%s' % parts.path}
        for key, values in parts.getquerydict().items():
            kwargs[key] = values[0]
        return schema.browse(self._connect(), Ref.TRACK, order=order, **kwargs)

    def _browse_artist(self, uri):
        parts = uritools.urisplit(uri)
        artist = 'local:%s' % parts.path
        role = parts.getquerydict().get('role', ['artist'])[0]
        return self._browse(**{role: artist})

    def _browse_genre(self, uri):
        parts = uritools.urisplit(uri)
        genre = uritools.uridecode(parts.path.partition(':')[2])
        return self._browse(genre=genre)

    def _browse_date(self, uri):
        parts = uritools.urisplit(uri)
        date = uritools.uridecode(parts.path.partition(':')[2])
        return self._browse(date=date)

    def _validate_artist(self, artist):
        if not artist.name:
            raise ValueError('Empty artist name')
        if artist.uri:
            uri = artist.uri
        elif artist.musicbrainz_id and self._config['use_artist_mbid_uri']:
            uri = _make_uri('artist', 'mbid', artist)
        else:
            uri = _make_uri('artist', 'md5', artist)
        return artist.copy(uri=uri)

    def _validate_album(self, album):
        if not album.name:
            raise ValueError('Empty album name')
        if album.uri:
            uri = album.uri
        elif album.musicbrainz_id and self._config['use_album_mbid_uri']:
            uri = _make_uri('album', 'mbid', album)
        else:
            uri = _make_uri('album', 'md5', album)
        artists = map(self._validate_artist, album.artists)
        return album.copy(uri=uri, artists=artists)

    def _validate_track(self, track):
        if not track.uri:
            raise ValueError('Empty track URI')
        if track.name:
            name = track.name
        else:
            name = self._decode(_TRACK_URI_RE.match(track.uri).group(2))
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

    def _decode(self, string):
        for encoding in self._config['encodings']:
            try:
                return uritools.uridecode(str(string), encoding=encoding)
            except UnicodeError:
                logger.debug('Not a %s string: %r', encoding, string)
        raise UnicodeError('No matching encoding found for %r' % string)


def _search_filters_from_uris(uris):
    # FIXME: new filter scheme!
    filters = []
    for uri in (uris or []):
        if uri.startswith('local:album:'):
            filters.append(('album', uri))
        elif uri.startswith('local:artist:'):
            splituri = uritools.urisplit(uri)
            artist = uritools.uriunsplit(splituri[0:3] + (None, None))
            role = splituri.getquerydict().get('role', ['artist'])[0]
            if role == 'artist':
                filters.append(('albumartist', artist))
            filters.append((role, artist))
        elif uri.startswith('local:genre:'):
            genre = uritools.uridecode(uri.rpartition(':')[2])
            filters.append(('genre', genre))
        elif uri.startswith('local:date:'):
            date = uritools.uridecode(uri.rpartition(':')[2])
            filters.append(('date', date))
            filters.append(('albumdate', date))
        else:
            logger.debug('Skipping search URI %s', uri)
    return filters


def _make_uri(type, variant, model):
    if variant == 'mbid':
        data = model.musicbrainz_id
    else:
        hash = hashlib.new(variant)
        hash.update(str(model))
        data = hash.hexdigest()
    assert data, 'uri data must not be null'
    return b'local:%s:%s:%s' % (type, variant, data)
