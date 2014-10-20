from __future__ import unicode_literals

import hashlib
import logging
import operator
import os
import os.path
import sqlite3
import uritools

from mopidy import local
from mopidy.local import translator  # FIXME: undocumented Mopidy API
from mopidy.models import Ref, SearchResult

from . import Extension, schema

DBNAME = 'library.db'

logger = logging.getLogger(__name__)


class SQLiteLibrary(local.Library):

    ROOT_PATH_URI = 'local:directory:'

    name = 'sqlite'

    def __init__(self, config):
        self._config = ext_config = config[Extension.ext_name]
        self._dbpath = os.path.join(Extension.get_data_dir(config), DBNAME)
        self._media_dir = config['local']['media_dir']
        self._directories = []
        for line in ext_config['directories']:
            name, uri = line.rsplit(None, 1)
            ref = Ref.directory(uri=uri, name=name)
            self._directories.append(ref)
        if ext_config['extract_images']:
            from .images import ImageDirectory
            self._images = ImageDirectory(config)
        else:
            self._images = None
        self._connection = None

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
            elif uri.startswith(self.ROOT_PATH_URI):
                return self._browse_directory_path(uri)
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
            if isinstance(values, basestring):
                q.append((field, values))
            else:
                q.extend((field, value) for value in values)
        filters = [f for uri in uris or [] for f in self._filters(uri) if f]
        with self._connect() as c:
            tracks = schema.search_tracks(c, q, limit, offset, exact, filters)
        uri = uritools.uricompose('local', path='search', query=q)
        return SearchResult(uri=uri, tracks=tracks)

    def begin(self):
        return schema.tracks(self._connect())

    def add(self, track):
        try:
            track = self._validate_track(track)
            if self._images and track.album:
                uri = translator.local_track_uri_to_file_uri(
                    track.uri, self._media_dir
                )
                album = track.album.copy(images=self._images.scan(uri))
                track = track.copy(album=album)
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

    def _browse_album(self, uri, order=('disc_no', 'track_no', 'name')):
        return schema.browse(self._connect(), Ref.TRACK, order, album=uri)

    def _browse_artist(self, uri):
        with self._connect() as c:
            albums = schema.browse(c, Ref.ALBUM, albumartist=uri)
            refs = schema.browse(c, artist=uri)
        uris, tracks = {ref.uri for ref in albums}, []
        for ref in refs:
            if ref.type == Ref.TRACK:
                tracks.append(ref)
            elif ref.type == Ref.ALBUM and ref.uri not in uris:
                uri = uritools.uricompose('local', None, 'directory', dict(
                    type=Ref.TRACK, album=ref.uri, artist=uri
                ))
                albums.append(Ref.directory(uri=uri, name=ref.name))
            else:
                logger.debug('Skipped SQLite browse result %s', ref.uri)
        albums.sort(key=operator.attrgetter('name'))
        return albums + tracks

    def _browse_directory(self, uri):
        query = dict(uritools.urisplit(str(uri)).getquerylist())
        type = query.pop('type', None)
        role = query.pop('role', None)

        # TODO: handle these in schema (generically)?
        if type == 'date':
            format = query.get('format', '%Y-%m-%d')
            return map(_dateref, schema.dates(self._connect(), format=format))
        if type == 'genre':
            return map(_genreref, schema.genres(self._connect()))

        roles = role or ('artist', 'albumartist')

        refs = []
        for ref in schema.browse(self._connect(), type, role=roles, **query):
            if ref.type == Ref.TRACK or (not query and not role):
                # FIXME: artist refs not browsable via mpd
                if ref.type == Ref.ARTIST:
                    refs.append(ref.copy(type=Ref.DIRECTORY))
                else:
                    refs.append(ref)
            elif ref.type == Ref.ALBUM:
                uri = uritools.uricompose('local', None, 'directory', dict(
                    query, type=Ref.TRACK, album=ref.uri
                ))
                refs.append(Ref.directory(uri=uri, name=ref.name))
            elif ref.type == Ref.ARTIST:
                uri = uritools.uricompose('local', None, 'directory', dict(
                    query, **{role: ref.uri}
                ))
                refs.append(Ref.directory(uri=uri, name=ref.name))
            else:
                logger.warn('Unexpected SQLite browse result: %r', ref)
        return refs

    def _browse_directory_path(self, uri):
        root = uritools.urisplit(str(uri)).getpath().partition(':')[2]
        refs, tracks = [], []
        for name in sorted(os.listdir(os.path.join(self._media_dir, root))):
            path = os.path.join(root, name)
            if os.path.isdir(os.path.join(self._media_dir, path)):
                uri = translator.path_to_local_directory_uri(path)
                refs.append(Ref.directory(uri=uri, name=name))
            else:
                uri = translator.path_to_local_track_uri(path)
                tracks.append(Ref.track(uri=uri, name=name))
        with self._connect() as c:
            refs += [track for track in tracks if schema.exists(c, track.uri)]
        return refs

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

    def _validate_track(self, track):
        if not track.uri:
            raise ValueError('Empty track URI')
        if track.name:
            name = track.name
        else:
            path = translator.local_track_uri_to_path(track.uri, b'')
            name = os.path.basename(path).decode('utf-8')
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
        if not uri or uri in (self.ROOT_DIRECTORY_URI, self.ROOT_PATH_URI):
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
            raise ValueError('Invalid search URI: %s', uri)

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
