"""I will modify this into mock someday.

By now it is tested manually. Test case includes:
1. Launch 1 Parent + 1 Child
2. Launch 1 Parent + 4 Children
3. Kill children by SIGINT. Child should be restarted.
4. Kill children by SIGTERM. Child should be restarted.
5. Kill parent by SIGINT. All should die
6. Kill parent by SIGTERM. All should die
7. Invoke Parent.stop after children are started. All should die.
8. Kill parent by SIGKILL (kill -9). All should die.
9. Service finishes in given time, rather than loop forever. Child should exit
   with return code 0. Parent exit after all children finish.

To send signal, use ``kill -s SIGXXX`` command in terminal.
"""

import os

import eventlet

from pyacc.common import config
from pyacc.server import process


def delayed_stop(parent):
    print "delayed_stop is running"
    eventlet.sleep(50)
    parent.stop()


class TestService(process.Service):
    def wait(self):
        for _ in xrange(3):
            print "TestService %s is doing stuff" % os.getpid()
            eventlet.sleep(3)

    def stop(self):
        print "TestService %s is stopping" % os.getpid()


if __name__ == '__main__':
    config.setup_logging()
    parent = process.Parent(TestService(), count=4)
    eventlet.spawn(delayed_stop, parent)
    parent.wait()