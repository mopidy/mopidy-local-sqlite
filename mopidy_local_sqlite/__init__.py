from __future__ import unicode_literals

import logging
import os

from mopidy import config, ext

__version__ = '0.10.1'

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
        schema['timeout'] = config.Integer(optional=True, minimum=1)
        schema['use_album_mbid_uri'] = config.Boolean()
        schema['use_artist_mbid_uri'] = config.Boolean()
        schema['search_limit'] = config.Integer(optional=True)
        # no longer used
        schema['extract_images'] = config.Deprecated()
        schema['image_dir'] = config.Deprecated()
        schema['image_base_uri'] = config.Deprecated()
        schema['album_art_files'] = config.Deprecated()
        return schema

    def setup(self, registry):
        from .library import SQLiteLibrary
        registry.add('local:library', SQLiteLibrary)

    @classmethod
    def get_or_create_data_dir(cls, config):
        try:
            data_dir = config['local']['data_dir']
        except KeyError:
            from mopidy.exceptions import ExtensionError
            raise ExtensionError('Mopidy-Local not enabled')
        path = os.path.join(data_dir, b'images')
        if not os.path.isdir(path):
            logger.info('Creating directory %s', path)
            os.makedirs(path, 0o755)
        return path
