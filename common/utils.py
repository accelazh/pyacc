import logging
import os
import sys

from pyacc.common import config


def empty_func(*args, **kwargs):
    pass


def normalize_config_path(config_path):
    possible_locations = [
        config_path,
        os.path.join('/etc', config.PROJECT_NAME, config_path)
    ]

    for path in possible_locations:
        if os.path.isfile(path):
            return os.path.abspath(path)
    raise IOError("Config file not found, path: %s" % config_path)


class WritableLogger(object):
    """Wrap the logger to be compatible with eventlet wsgi server needs"""

    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level

    def write(self, msg):
        self.logger.log(self.level, msg.rstrip())

