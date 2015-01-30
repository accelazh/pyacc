from pyacc.tests.patch.mdc import cls_c


def decorator(func):
    def wrap(*args, **kwargs):
        print "decorator called"
        func(*args, **kwargs)
    return wrap


class B(object):

    def __init__(self, val):
        self.val = val

    def f1(self):
        print "B.f1 invoked: self=%s" % self
        self.val -= 1
        self.f2()
        #raise ValueError('test')

    @decorator
    def f2(self):
        print "B.f2 invoked: self=%s" % self
        self.val -= 1
        cls_c.C(self.val-1, self.val-2, kw=1, kw2=2)
