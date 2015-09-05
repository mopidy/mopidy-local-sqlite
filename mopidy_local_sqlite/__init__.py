from __future__ import unicode_literals

import logging
import os

from mopidy import config, ext

__version__ = '1.0.0'

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
        schema['use_artist_sortname'] = config.Boolean()
        # no longer used
        schema['search_limit'] = config.Deprecated()
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
        data_dir = cls().get_data_dir(config)
        migrate_old_data_dir(config, data_dir)
        return data_dir


def migrate_old_data_dir(config, new_dir):
    # Remove this method when we're confident most users have upgraded away
    # from Mopidy 1.0.
    old_dir = os.path.join(config['core']['data_dir'], b'local', b'sqlite')
    if not os.path.isdir(old_dir):
        return
    logger.info('Migrating Mopidy-Local-SQLite to new data dir')
    for filename in os.listdir(old_dir):
        old_path = os.path.join(old_dir, filename)
        new_path = os.path.join(new_dir, filename)
        logger.info('Moving %r to %r', old_path, new_path)
        os.rename(old_path, new_path)
    os.rmdir(old_dir)
