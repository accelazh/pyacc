"""I will modify this into mock someday.

By now it is tested manually. Test case includes:
1. Start my wsgi server on one side. Use curl to connect on another side.
   Curl should return the message and env information.
"""

import pprint

from pyacc.common import config
from pyacc.server import process
from pyacc.server import wsgi


def wsgi_app(env, start_response):
    start_response('200 OK', [('Content-Type', 'text/json')])
    message = {
        'message': 'hello world',
        'env': env
    }
    return [pprint.pformat(message)]


if __name__ == '__main__':
    config.setup_logging()
    server = wsgi.Server(name=__name__, app=wsgi_app)
    parent = process.Parent(server, count=4)
    parent.wait()