from __future__ import unicode_literals

import logging
import os

from mopidy import config, ext

__version__ = '0.7.3'

logger = logging.getLogger(__name__)


class Extension(ext.Extension):

    dist_name = 'Mopidy-Local-SQLite'
    ext_name = 'local-sqlite'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        schema['directories'] = config.List()
        schema['encodings'] = config.List()
        schema['timeout'] = config.Integer(optional=True, minimum=1)
        schema['use_album_mbid_uri'] = config.Boolean()
        schema['use_artist_mbid_uri'] = config.Boolean()
        schema['extract_images'] = config.Boolean()
        schema['image_dir'] = config.String()
        schema['image_base_uri'] = config.String(optional=True)
        schema['album_art_files'] = config.List(optional=True)

        # no longer used
        schema['foreign_keys'] = config.Deprecated()
        schema['hash'] = config.Deprecated()
        schema['default_image_extension'] = config.Deprecated()

        return schema

    def setup(self, registry):
        from .library import SQLiteLibrary
        from .http import factory
        registry.add('local:library', SQLiteLibrary)
        registry.add('http:app', {'name': 'sqlite', 'factory': factory})

    @classmethod
    def make_data_dir(cls, config, *paths):
        # Not using mopidy.utils.path.get_or_create_dir, since that's
        # an undocumented, private Mopidy API
        path = os.path.join(config['local']['data_dir'], b'sqlite', *paths)
        if not os.path.isdir(path):
            logger.info('Creating directory %s', path)
            os.makedirs(path, 0755)
        return path
