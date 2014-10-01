from __future__ import unicode_literals

import logging
import os
import tornado.web

logger = logging.getLogger(__name__)


class IndexHandler(tornado.web.RequestHandler):

    def initialize(self, images):
        self._images = images

    def get(self, path):
        return self.render('index.html', images=self._images.uris())

    def get_template_path(self):
        return os.path.join(os.path.dirname(__file__), 'www')


def factory(config, core):
    from . import Extension
    from .images import ImageDirectory
    logger.info('Starting %s Image Server', Extension.dist_name)
    images = ImageDirectory(config)

    return [
        (r'/(index.html)?', IndexHandler, {'images': images}),
        (r'/images/(.*)', tornado.web.StaticFileHandler, {'path': images.root})
    ]
