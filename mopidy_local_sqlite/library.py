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
        return 0

    def lookup(self, uri):
        return None

    def browse(self, uri):
        return []

    def search(self, query=None, limit=100, offset=0, uris=None, exact=False):
        return SearchResult(tracks=[])

    def begin(self):
        pass

    def add(self, track):
        pass

    def remove(self, uri):
        pass

    def flush(self):
        return False

    def close(self):
        pass

    def clear(self):
        return True
