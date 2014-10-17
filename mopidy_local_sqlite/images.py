from __future__ import unicode_literals

import glob
import hashlib
import imghdr
import logging
import os
import uritools

from mopidy.audio.scan import Scanner
from mopidy.utils.path import get_or_create_file, uri_to_path

from . import Extension

logger = logging.getLogger(__name__)


class ImageDirectory(object):

    def __init__(self, config):
        ext_config = config[Extension.ext_name]
        if ext_config['image_dir']:
            self.root = ext_config['image_dir']
        else:
            self.root = Extension.get_data_dir(config, b'images')
        self._base_uri = ext_config['image_base_uri']
        self._patterns = map(str, ext_config['album_art_files'])
        self._scanner = None

    def scan(self, uri):
        if not self._scanner:
            self._scanner = Scanner()
        data = self._scanner.scan(uri)
        logger.debug('Scanning for images: %r', data)
        images = []
        for image in data['tags'].get('image', []):
            try:
                images.append(self._get_or_create_image(None, image.data))
            except Exception as e:
                logger.warn('Cannot extract image from %s: %s', uri, e)
        dirname = os.path.dirname(uri_to_path(uri))
        for pattern in self._patterns:
            for path in glob.glob(os.path.join(dirname, pattern)):
                try:
                    images.append(self._get_or_create_image(path))
                except Exception as e:
                    logger.warn('Cannot read album art from %s: %s', path, e)
        return images

    def cleanup(self, uris):
        if not os.path.isdir(self.root):
            return
        uris = frozenset(uris)
        for root, _, files in os.walk(self.root):
            for name in files:
                if self.geturi(name) not in uris:
                    path = os.path.join(root, name)
                    logger.info('Deleting file %s', path)
                    os.remove(path)

    def clear(self):
        if not os.path.isdir(self.root):
            return
        for root, dirs, files in os.walk(self.root, topdown=False):
            for name in dirs:
                os.rmdir(os.path.join(root, name))
            for name in files:
                os.remove(os.path.join(root, name))

    def uris(self):
        if not os.path.isdir(self.root):
            raise StopIteration
        for _, _, files in os.walk(self.root):
            for name in files:
                yield self.geturi(name)

    def geturi(self, filename):
        return uritools.urijoin(self._base_uri, filename)

    def _get_or_create_image(self, path, data=None):
        what = imghdr.what(path, data)
        if not what:
            raise ValueError('Unknown image type')
        if not data:
            data = open(path).read()
        name = hashlib.md5(data).hexdigest() + '.' + what
        path = os.path.join(self.root, name)
        get_or_create_file(str(path), True, data)
        return self.geturi(name)
