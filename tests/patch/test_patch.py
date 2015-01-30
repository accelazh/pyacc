# Manual tests. Tested class method, module method and decorators. The argument
# decorate=True/False and return_value=XXX is tested.

from pyacc.tests.patch.mda.cls_a import A
from pyacc.common.patch import Patch


a = A()
a.f1()

print '--------decorate----------'

with Patch('pyacc.tests.patch.mdb.cls_b.B.f2') as mock:
    a = A()
    a.f1()
    print 'mock trace %s' % mock

print '----------break-----------'

with Patch('pyacc.tests.patch.mdb.cls_b.B.f2', decorate=False) as mock:
    a = A()
    a.f1()
    print 'mock trace %s' % mock

print '----------return val-----------'

with Patch('pyacc.tests.patch.mdb.cls_b.B.f2', decorate=False, return_value=7) as mock:
    a = A()
    a.f1()
    print 'mock trace %s' % mock

print '--------decorate C----------'

with Patch('pyacc.tests.patch.mdc.cls_c.C') as mock:
    a = A()
    a.f1()
    print 'mock trace %s' % mock

print '----------break C-----------'

with Patch('pyacc.tests.patch.mdc.cls_c.C', decorate=False) as mock:
    a = A()
    a.f1()
    print 'mock trace %s' % mock

print '----------return val C-----------'

with Patch('pyacc.tests.patch.mdc.cls_c.C', decorate=False, return_value=7) as mock:
    a = A()
    a.f1()
    print 'mock trace %s' % mock

print '----------path error-----------'

with Patch('pyacc.tests.patch.mdc.cls_c.E', decorate=False, return_value=7) as mock:
    a = A()
    a.f1()
    print 'mock trace %s' % mock

print '----------------------------'

a = A()
a.f1()

