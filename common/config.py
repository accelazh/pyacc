import logging


PROJECT_NAME = 'pyacc'
LOGGING_FORMAT = {
    'format': '%(asctime)s:%(process)d:%(levelname)s: %(message)s',
    'datefmt': '%b %d %H:%M:%S',
}


def setup_logging(level=logging.DEBUG):
    logging.basicConfig(level=level, **LOGGING_FORMAT)