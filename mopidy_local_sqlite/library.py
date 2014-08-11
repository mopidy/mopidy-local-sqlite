from __future__ import unicode_literals

import logging
import os

from mopidy import local
from mopidy.models import SearchResult

logger = logging.getLogger(__name__)


class SQLiteLibrary(local.Library):
    name = 'sqlite'

    def __init__(self, config):
        self._data_dir = os.path.join(config['local']['data_dir'], b'sqlite')

    def load(self):
        logger.info('sqlite: load()')
        return 0

    def lookup(self, uri):
        logger.info('sqlite: lookup(%r)', uri)
        return None

    def browse(self, uri):
        logger.info('sqlite: browse(%r)', uri)
        return []

    def search(self, query=None, limit=100, offset=0, uris=None, exact=False):
        logger.info('sqlite: search(%r, %r)', query, uris)
        return SearchResult(tracks=[])

    def begin(self):
        logger.info('sqlite: begin()')
        return iter([])

    def add(self, track):
        logger.info('sqlite: add(%r)', track)
        pass

    def remove(self, uri):
        logger.info('sqlite: remove(%r)', uri)
        pass

    def flush(self):
        logger.info('sqlite: flush()')
        return False

    def close(self):
        logger.info('sqlite: close()')
        pass

    def clear(self):
        logger.info('sqlite: clear()')
        return True
