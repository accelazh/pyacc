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


class Patch(object):
    """Monkey patch specified class method to your method. Can be used in
    mock test.

    Example::

        def your_method(*args, **kwargs):
            print "do what ever you want"

        with Patch('module_path.class_name.method_name', your_method):
            print "module_path.class_name.method_name will not be called"
            print "your_method will be called instead"

    Note that if ``module_path.class_name.method_name`` has decorators, they
    will be replace together.
    """

    def __init__(self, path, new_method=empty_func):
        self.path = path
        self.new_method = new_method

    @staticmethod
    def patch(path, new_method):
        class_path, _separator, method_name = path.rpartition('.')
        module_path, _separator, class_name = class_path.rpartition('.')
        __import__(module_path)
        cls = getattr(sys.modules[module_path], class_name)

        original_method = getattr(cls, method_name)
        setattr(cls, method_name, new_method)
        return original_method

    def __enter__(self):
        self.original_method = self.patch(self.path, self.new_method)
        return self

    def __exit__(self, type, value, traceback):
        self.patch(self.path, self.original_method)


