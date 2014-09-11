from __future__ import unicode_literals

import logging
import os

import tornado.web

logger = logging.getLogger(__name__)


def _get_image_path(config):
    from . import Extension
    data_dir = config['local']['data_dir']
    image_dir = config[Extension.ext_name]['image_dir']
    return os.path.join(data_dir, image_dir)


class IndexHandler(tornado.web.RequestHandler):

    def initialize(self, config):
        self._path = _get_image_path(config)

    def get(self, path):
        images = []
        if os.path.isdir(self._path):
            for _, _, filenames in os.walk(self._path):
                images.extend(map(lambda name: 'images/%s' % name, filenames))
        return self.render('index.html', images=images)

    def get_template_path(self):
        return os.path.join(os.path.dirname(__file__), 'www')


def factory(config, core):
    images = _get_image_path(config)
    logger.info('Starting Mopidy-Local-SQLite Image Server for %s', images)
    return [
        (r'/(index.html)?', IndexHandler, {'config': config}),
        (r'/images/(.*)', tornado.web.StaticFileHandler, {'path': images})
    ]
