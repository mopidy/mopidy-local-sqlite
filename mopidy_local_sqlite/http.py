from __future__ import unicode_literals

import logging
import os
import tornado.web

logger = logging.getLogger(__name__)


class IndexHandler(tornado.web.RequestHandler):

    def initialize(self, images):
        self._images = images

    def get(self, path):
        if self._images:
            return self.render('index.html', images=self._images.uris())
        else:
            return self.render('index.html', images=None)

    def get_template_path(self):
        return os.path.join(os.path.dirname(__file__), 'www')


def factory(config, core):
    from . import Extension
    from .images import ImageDirectory

    if not config[Extension.ext_name]['extract_images']:
        return [(r'/(index.html)?', IndexHandler, {'images': None})]
    try:
        images = ImageDirectory(config)
    except Exception:
        # FIXME: workaround for issue #30 (local not enabled)
        return [(r'/(index.html)?', IndexHandler, {'images': None})]
    logger.info('Starting %s Image Server', Extension.dist_name)
    return [
        (r'/(index.html)?', IndexHandler, {'images': images}),
        (r'/images/(.*)', tornado.web.StaticFileHandler, {'path': images.root})
    ]
