
from pyacc.tests.patch.mdb import cls_b


class A(object):

    def __init__(self):
        self.val = 99

    def f1(self):
        print "A.f1 invoked: self=%s" % self
        self.val -= 1
        self.f2()

    def f2(self):
        print "A.f2 invoked: self=%s" % self
        b = cls_b.B(self.val)
        b.f1()
        ret = b.f2()
        print "b.f2() returns %s" % ret
