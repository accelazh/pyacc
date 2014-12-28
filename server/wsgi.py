import logging
import socket

import eventlet.wsgi
from paste import deploy
import routes.middleware
import webob
import webob.dec
import webob.exc

from pyacc.common import utils
from pyacc.server import process


LOG = logging.getLogger(__name__)


class Loader(object):
    """Load wsgi applications from paste configurations"""

    def __init__(self, config_path=None):
        utils.normalize_config_path(config_path)
        self.config_path = config_path

    def load_app(self, name):
        return deploy.loadapp("config:%s" % self.config_path, name=name)


# TODO Finished, but not tested
class Server(process.Service):
    """The server to run a WSGI application.

    It internally runs by eventlet.wsgi.server. Greenthreads will handle multiple
    concurrent client connects.
    """

    def __init__(self, name=None, app=None, host='0.0.0.0', port=1234,
                 pool_size=1024, backlog=128, family=socket.AF_INET,
                 client_socket_timeout=900, max_header_line=None):
        self.name = name
        self.app = app
        self.host = host
        self.port = port
        self.pool_size = pool_size
        self.backlog = backlog
        self.family = family
        self.client_socket_timeout = client_socket_timeout
        self._wsgi_logger = utils.WritableLogger(
            logging.getLogger("eventlet.wsgi.server"))

        if not max_header_line:
            self.max_header_line = eventlet.wsgi.MAX_HEADER_LINE
        eventlet.wsgi.MAX_HEADER_LINE = self.max_header_line

        self._pool = eventlet.GreenPool(size=self.pool_size)
        self._socket = eventlet.listen((self.host, self.port), backlog=self.backlog,
                                       family=self.family)
        (self.host, self.port) = self._socket.getsockname()[0:2]
        self._wsgi = None

    def _setup_socket(self):
        # Duplicate sever socket to keep underlying file descriptor usable after
        # others exit
        self._socket_dup = self._socket.dup()
        self._socket_dup.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Will be invoked in child process
    def wait(self):
        self._setup_socket()

        wsgi_kwargs = {
            'sock': self._socket_dup,
            'site': self.app,
            'custom_pool': self._pool,
            'log': self._wsgi_logger,
            'socket_timeout': self.client_socket_timeout,
            'keepalive': True,
        }

        LOG.info("Starting WSGI server")
        # Server multiple client connections concurrently using greenthreads
        self._wsgi = eventlet.wsgi.server(**wsgi_kwargs)

    def stop(self):
        LOG.info("Stopping WSGI server")


# TODO Not finished
# TODO I need to implement the wsgi rest controller class. Like
# TODO openstack/cinder.api.openstack.wsgi
# TODO The user would need to use mapper.resource() to connect url to objects
# TODO After all, my process.py would boot up the wsgi server
# TODO I start to think, why not just use web.py?
class Router(object):

    def __init__(self, mapper):
        self.mapper = mapper
        self._router = routes.middleware.RoutesMiddleware(self._dispatch, self.mapper)

    @webob.dec.wsgify(RequestClass=webob.Request)
    def __call__(self, request):
        return self._router

    @staticmethod
    @webob.dec.wsgify(RequestClass=webob.Request)
    def _dispatch(request):
        url, match = request.environ['wsgiorg.routing_args']
        if not match:
            return webob.exc.HTTPNotFound()
        app = match['controller']
        return app

# TODO I can use web.py as wsgi application and Apache+mod_wsgi as multiprocess server.
# TODO For web.py: application = web.application(urls, globals()).wsgifunc()
# TODO See http://webpy.org/cookbook/mod_wsgi-apache.zh-cn
# TODO Or, I can replace my process.py+Server with Spawning
