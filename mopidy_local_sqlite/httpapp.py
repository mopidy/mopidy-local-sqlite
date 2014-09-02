from __future__ import unicode_literals

import logging
import os

import tornado.web

logger = logging.getLogger(__name__)


def _get_images_path(config):
    from . import Extension
    data_dir = config['local']['data_dir']
    image_dir = config[Extension.ext_name]['image_dir']
    return os.path.join(data_dir, image_dir)


def factory(config, core):
    images = _get_images_path(config)
    logger.info('Creating static HTTP handler for %s', images)
    return [
        # TODO: index handler
        (r'/images/(.*)', tornado.web.StaticFileHandler, {'path': images})
    ]
