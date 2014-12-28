""" Provide a general tool to implement multiprocess services.

The model consists of 1 parent process and N child processes. A Service instance is
run by each child process. For Service you have to implement the wait/stop methods.
You are supposed to use eventlet greenthreads non-blockingly.

Signals of parent process and child process are handled. Zombine process problem is
handled. The parent process ensures that there are always as many child processes
running as the count you specified. Child process ensures to exit if parent dies.

Further I want to implement a WSGI REST api server based on this.

P.S. I've tried using multiprocessing.Process to implement this multiprocess model
but found out that it has problems and I need os.fork().
"""

import abc
import errno
import logging
import os
import signal
import six
import sys

import eventlet


LOG = logging.getLogger(__name__)


def _sighup_supported():
    return hasattr(signal, 'SIGHUP')


def _signo_to_name(signo):
    signals = {signal.SIGTERM: 'SIGTERM',
               signal.SIGINT: 'SIGINT'}
    if _sighup_supported():
        signals[signal.SIGHUP] = 'SIGHUP'
    if signo in signals:
        return signals[signo]
    else:
        return 'UNKNOWN'


def _setup_signal_handler(handler):
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    if _sighup_supported():
        signal.signal(signal.SIGHUP, handler)


@six.add_metaclass(abc.ABCMeta)
class Service(object):
    """ Service to be run by Child processes.

    You don't have to subclass this class to use Parent / Child. Anyway, provide
    below wait/stop methods.

    The Service is supposed to be implemented using eventlet greenthreads. Run multiple
    tasks in greenthreads and wait() for them.
    """

    @abc.abstractmethod
    def stop(self):
        return

    @abc.abstractmethod
    def wait(self):
        return


class Parent(object):
    """Parent represents the parent process.

    Parent process starts child process, wait for them to exit and restart them
    ensure the count of child processes. Signals are handled for proper cleaning
    up.
    """

    def __init__(self, service, count=1, wait_interval=0.01):
        if count < 0:
            raise ValueError("Child count %d should not be less than zero" % count)

        self.service = service
        self.count = count
        self.wait_interval = wait_interval

        self.signal_caught = None
        self.signal_frame = None
        self.children = {}
        self.completed_children = {}
        self.running = True
        _setup_signal_handler(self._signal_handler)

        # use pipe to stop child after parent dies
        self.pipe_read_fd, self.pipe_write_fd = os.pipe()

    def _signal_handler(self, signo, frame):
        LOG.info('Parent signal caught: %s', _signo_to_name(signo))
        self.signal_caught = signo
        self.signal_frame = frame
        self.running = False
        _setup_signal_handler(signal.SIG_DFL)

    def _wait_child(self):
        try:
            pid, status = eventlet.green.os.waitpid(0, os.WNOHANG)
            if not pid:
                return None, None
        except OSError as exc:
            if exc.errno not in (errno.ECHILD, errno.EINTR):
                raise
            return None, None

        return_code = os.WEXITSTATUS(status)
        if os.WIFSIGNALED(status):
            signo = os.WTERMSIG(status)
            LOG.info('Child process terminated by signal %(sig_name)s with '
                     'return code %(return_code)d',
                     {'sig_name': _signo_to_name(signo),
                      'return_code': return_code})
        else:
            LOG.info('Child process exited with return code %(return_code)d',
                     {'return_code': return_code})

        return pid, return_code

    def _complete_child(self, pid, return_code):
        child = self.children.pop(pid, None)
        if child and return_code == 0:
            self.completed_children[pid] = child

    def _start_child(self):
        child = Child(self.service, pipe_read_fd=self.pipe_read_fd,
                      pipe_write_fd=self.pipe_write_fd)
        pid = child.start()
        self.children[pid] = child
        LOG.info('Child process started')

    def _ensure_child_count(self):
        while len(self.children) + len(self.completed_children) < self.count:
            self._start_child()
            # make sure we don't fork too quickly
            eventlet.sleep(self.wait_interval)

    def _handle_child_exit(self):
        pid, return_code = self._wait_child()
        self._complete_child(pid, return_code)

    def wait(self):
        try:
            while self.running:
                self._ensure_child_count()
                self._handle_child_exit()
                if len(self.completed_children) == self.count:
                    break
                eventlet.sleep(self.wait_interval)
        except eventlet.greenlet.GreenletExit:
            LOG.info("Method wait called after green thread killed. Stopping.")
        self.stop()

    def stop(self):
        self.running = False
        for pid in self.children.keys():
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError as exc:
                if exc.errno != errno.ESRCH:
                    raise

        if len(self.children) > 0:
            children_pid_str_list = [str(i) for i in self.children.keys()]
            LOG.info('Waiting child(ren) %s to exit',
                     ', '.join(children_pid_str_list))
        while len(self.children) > 0:
            self._handle_child_exit()


class SignalExit(SystemExit):
    def __init__(self, signo, code=1):
        super(SignalExit, self).__init__(code)
        self.signo = signo

    def __str__(self):
        return ("signal=%(sig_name)s, code=%(code)d" %
                {'sig_name': _signo_to_name(self.signo),
                 'code': self.code})


class Child(object):
    """Child represents the child process started by os.fork().

    In each child process, a service is run. You can use eventlet greenthreads in
    the service. Signals are handled for proper cleaning up.
    """

    def __init__(self, service, pipe_read_fd, pipe_write_fd):
        self.service = service
        self.pipe_read_fd = pipe_read_fd
        self.pipe_write_fd = pipe_write_fd

        self.pid = None
        self.signal_caught = None
        self.signal_frame = None
        self.pipe_read = None

    def _signal_handler(self, signo, frame):
        LOG.info('Child %(pid)d signal caught: %(sig_name)s',
                 {'pid': self.pid, 'sig_name': _signo_to_name(signo)})
        self.signal_caught = signo
        self.signal_frame = frame
        _setup_signal_handler(signal.SIG_DFL)

        try:
            self.service.stop()
        except:
            LOG.exception('Child service raised error when stopping')
            raise
        finally:
            raise SignalExit(signo)

    def _setup_pipe_watcher(self):
        os.close(self.pipe_write_fd)
        self.pipe_read = eventlet.greenio.GreenPipe(self.pipe_read_fd, 'r')
        eventlet.spawn_n(self._pipe_watcher)

    def _pipe_watcher(self):
        """Make sure child exits if parent dies, using pipe"""

        self.pipe_read.read()
        LOG.info('Parent process died unexpectedly. Child exiting.')
        sys.exit(1)

    def start(self):
        pid = os.fork()
        if pid == 0:
            self.pid = os.getpid()
            # Reopen eventlet hub to make sure we don't share an epoll fd between
            # parent and children
            eventlet.hubs.use_hub()
            _setup_signal_handler(self._signal_handler)
            self._setup_pipe_watcher()
            try:
                self.service.wait()
            except:
                LOG.exception('Child service raised error when start and wait')
                raise
            sys.exit(0)
        else:
            self.pid = pid
            return pid
