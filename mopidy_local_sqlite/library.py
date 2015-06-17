from __future__ import unicode_literals

import hashlib
import logging
import operator
import os
import os.path
import sqlite3
import sys

from mopidy import local
from mopidy.exceptions import ExtensionError
from mopidy.local import translator
from mopidy.models import Ref, SearchResult

import uritools

from . import Extension, schema


# changed in Mopidy v1.1
try:
    from mopidy.local.translator import path_to_file_uri
except ImportError:
    from mopidy.utils.path import path_to_uri as path_to_file_uri
try:
    from mopidy.local.translator import local_uri_to_path
except ImportError:
    # missing from mopidy.local.translator
    def local_uri_to_path(uri, media_dir):
        from mopidy.utils.path import uri_to_path
        if not uri.startswith('local:directory:'):
            raise ValueError('Invalid URI.')
        file_path = uri_to_path(uri).split(b':', 1)[1]
        return os.path.join(media_dir, file_path)

URI_PREFIX = 'local:'

logger = logging.getLogger(__name__)


class SQLiteLibrary(local.Library):

    ROOT_PATH_URI = 'local:directory:'

    name = 'sqlite'

    def __init__(self, config):
        self._config = ext_config = config[Extension.ext_name]
        self._data_dir = Extension.get_or_create_data_dir(config)
        try:
            self._media_dir = config['local']['media_dir']
            excluded = config['local']['excluded_file_extensions']
            self._excluded_ext = tuple(bytes(e.lower()) for e in excluded)
        except KeyError:
            raise ExtensionError('Mopidy-Local not enabled')
        self._directories = []
        for line in ext_config['directories']:
            name, uri = line.rsplit(None, 1)
            ref = Ref.directory(uri=uri, name=name)
            self._directories.append(ref)
        self._dbpath = os.path.join(self._data_dir, b'library.db')
        self._connection = None

    def load(self):
        with self._connect() as connection:
            version = schema.load(connection)
            logger.debug('Using SQLite database schema v%s', version)
            return schema.count_tracks(connection)

    def lookup(self, uri):
        if uri.startswith('local:album'):
            return list(schema.lookup(self._connect(), Ref.ALBUM, uri))
        elif uri.startswith('local:artist'):
            return list(schema.lookup(self._connect(), Ref.ARTIST, uri))
        elif uri.startswith('local:track'):
            return list(schema.lookup(self._connect(), Ref.TRACK, uri))
        else:
            logger.error('Invalid lookup URI %s', uri)
            return []

    def browse(self, uri):
        try:
            if uri == self.ROOT_DIRECTORY_URI:
                return self._directories
            elif uri.startswith(self.ROOT_PATH_URI):
                return self._browse_path(uri)
            elif uri.startswith('local:directory'):
                return self._browse_directory(uri)
            elif uri.startswith('local:artist'):
                return self._browse_artist(uri)
            elif uri.startswith('local:album'):
                return self._browse_album(uri)
            else:
                raise ValueError('Invalid browse URI')
        except Exception as e:
            logger.error('Error browsing %s: %s', uri, e)
            return []

    def search(self, query=None, limit=100, offset=0, uris=None, exact=False):
        q = []
        for field, values in (query.items() if query else []):
            q.extend((field, value) for value in values)
        # temporary workaround until Mopidy core sets limit
        if self._config['search_limit'] is not None:
            limit = self._config['search_limit']
        filters = [f for uri in uris or [] for f in self._filters(uri) if f]
        with self._connect() as c:
            tracks = schema.search_tracks(c, q, limit, offset, exact, filters)
        uri = uritools.uricompose('local', path='search', query=q)
        return SearchResult(uri=uri, tracks=tracks)

    def get_distinct(self, field, query=None):
        q = []
        for key, values in (query.items() if query else []):
            q.extend((key, value) for value in values)
        return set(schema.list_distinct(self._connect(), field, q))

    def begin(self):
        return schema.tracks(self._connect())

    def add(self, track):
        try:
            track = self._validate_track(track)
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
        self._connection.commit()
        self._connection.close()
        self._connection = None

    def clear(self):
        try:
            schema.clear(self._connect())
            return True
        except sqlite3.Error as e:
            logger.error('Error clearing SQLite database: %s', e)
            return False

    def _connect(self):
        if not self._connection:
            self._connection = sqlite3.connect(
                self._dbpath,
                factory=schema.Connection,
                timeout=self._config['timeout'],
                check_same_thread=False,
            )
        return self._connection

    def _browse_album(self, uri, order=('disc_no', 'track_no', 'name')):
        return schema.browse(self._connect(), Ref.TRACK, order, album=uri)

    def _browse_artist(self, uri, order=('type', 'name')):
        with self._connect() as c:
            albums = schema.browse(c, Ref.ALBUM, order, albumartist=uri)
            refs = schema.browse(c, order=order, artist=uri)
        album_uris, tracks = {ref.uri for ref in albums}, []
        for ref in refs:
            if ref.type == Ref.ALBUM and ref.uri not in album_uris:
                albums.append(Ref.directory(
                    uri=uritools.uricompose('local', None, 'directory', dict(
                        type=Ref.TRACK, album=ref.uri, artist=uri
                    )),
                    name=ref.name
                ))
            elif ref.type == Ref.TRACK:
                tracks.append(ref)
            else:
                logger.debug('Skipped SQLite browse result %s', ref.uri)
        albums.sort(key=operator.attrgetter('name'))
        return albums + tracks

    def _browse_directory(self, uri, order=('type', 'name')):
        query = dict(uritools.urisplit(uri).getquerylist())
        type = query.pop('type', None)
        role = query.pop('role', None)

        # TODO: handle these in schema (generically)?
        if type == 'date':
            format = query.get('format', '%Y-%m-%d')
            return map(_dateref, schema.dates(self._connect(), format=format))
        if type == 'genre':
            return map(_genreref, schema.list_distinct(self._connect(), 'genre'))  # noqa

        # Fix #38: keep sort order of album tracks; this also applies
        # to composers and performers
        if type == Ref.TRACK and 'album' in query:
            order = ('disc_no', 'track_no', 'name')

        roles = role or ('artist', 'albumartist')  # FIXME: re-think 'roles'...

        refs = []
        for ref in schema.browse(self._connect(), type, order, role=roles, **query):  # noqa
            if ref.type == Ref.TRACK or (not query and not role):
                refs.append(ref)
            elif ref.type == Ref.ALBUM:
                refs.append(Ref.directory(uri=uritools.uricompose(
                    'local', None, 'directory', dict(query, type=Ref.TRACK, album=ref.uri)  # noqa
                ), name=ref.name))
            elif ref.type == Ref.ARTIST:
                refs.append(Ref.directory(uri=uritools.uricompose(
                    'local', None, 'directory', dict(query, **{role: ref.uri})
                ), name=ref.name))
            else:
                logger.warn('Unexpected SQLite browse result: %r', ref)
        return refs

    def _browse_path(self, uri, encoding=sys.getfilesystemencoding()):
        root = local_uri_to_path(uri, b'')
        dirs, tracks = [], []
        for file in sorted(os.listdir(os.path.join(self._media_dir, root))):
            path = os.path.join(root, file)
            name = file.decode(encoding, 'replace')
            if os.path.isdir(os.path.join(self._media_dir, path)):
                uri = translator.path_to_local_directory_uri(path)
                dirs.append(Ref.directory(uri=uri, name=name))
            elif not path.lower().endswith(self._excluded_ext):
                uri = path_to_file_uri(os.path.join(self._media_dir, path))
                tracks.append(Ref.track(uri=uri, name=name))
            else:
                logger.debug('Skipped %s: File extension excluded.', path)
        return dirs + tracks

    def _validate_artist(self, artist):
        if not artist.name:
            raise ValueError('Empty artist name')
        uri = artist.uri or self._model_uri('artist', artist)
        return artist.copy(uri=uri)

    def _validate_album(self, album):
        if not album.name:
            raise ValueError('Empty album name')
        uri = album.uri or self._model_uri('album', album)
        artists = map(self._validate_artist, album.artists)
        return album.copy(uri=uri, artists=artists)

    def _validate_track(self, track, encoding=sys.getfilesystemencoding()):
        if not track.uri:
            raise ValueError('Empty track URI')
        if track.name:
            name = track.name
        else:
            path = translator.local_track_uri_to_path(track.uri, b'')
            name = os.path.basename(path).decode(encoding, errors='replace')
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

    def _filters(self, uri):
        if uri in (URI_PREFIX, self.ROOT_DIRECTORY_URI, self.ROOT_PATH_URI):
            return []
        elif uri.startswith(self.ROOT_PATH_URI):
            return [{'uri': uri.replace('directory', 'track', 1) + '/*'}]
        elif uri.startswith('local:directory'):
            return [dict(uritools.urisplit(uri).getquerylist())]
        elif uri.startswith('local:artist'):
            return [{'artist': uri}, {'albumartist': uri}]
        elif uri.startswith('local:album'):
            return [{'album': uri}]
        else:
            logger.warn('Invalid search URI: %s', uri)
            return []

    def _model_uri(self, type, model):
        if model.musicbrainz_id and self._config['use_%s_mbid_uri' % type]:
            return 'local:%s:mbid:%s' % (type, model.musicbrainz_id)
        digest = hashlib.md5(str(model)).hexdigest()
        return 'local:%s:md5:%s' % (type, digest)


def _dateref(date):
    return Ref.directory(
        uri=uritools.uricompose('local', None, 'directory', {'date': date}),
        name=date
    )


def _genreref(genre):
    return Ref.directory(
        uri=uritools.uricompose('local', None, 'directory', {'genre': genre}),
        name=genre
    )
