from __future__ import unicode_literals

from mopidy_local_sqlite import Extension


def test_get_default_config():
    ext = Extension()
    config = ext.get_default_config()
    assert '[local-sqlite]' in config
    assert 'enabled = true' in config


def test_get_config_schema():
    ext = Extension()
    schema = ext.get_config_schema()
    assert 'directories' in schema
    assert 'timeout' in schema
    assert 'use_album_mbid_uri' in schema
    assert 'use_artist_mbid_uri' in schema
    assert 'search_limit' in schema
