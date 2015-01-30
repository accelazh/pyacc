import sys


def empty_func(*args, **kwargs):
    return None


class Patch(object):
    """Monkey patch specified class method to call arguments and return value.

    Example::

        with Patch('module_path.class_name.method_name') as mock:
            # something that invokes 'module_path.class_name.method_name'
            ...
            print mock['args'], mock['kwargs'], mock['return_value']

        with Patch('module_path.class_name.method_name', decorate=False) as mock:
            # something that invokes 'module_path.class_name.method_name'
            # 'decorate=False' prevents the original 'module_path.class_name
            .method_name' from executing. I.e. it is not decorated, but replaced
            (to an empty function).
            ...
            # mock['return_value'] should be None
            print mock['args'], mock['kwargs'], mock['return_value']

        with Patch('module_path.class_name.method_name',
                   decorate=False,
                   return_value=XXX) as mock:
            # something that invokes 'module_path.class_name.method_name'
            # decorate=False & return_value=XXX will make the mocked method
            # return XXX rather than None. The return value could be used by
            # its invokers.
            ...
            # mock['return_value'] should be XXX
            print mock['args'], mock['kwargs'], mock['return_value']

    Note that if ``module_path.class_name.method_name`` has decorators, they
    will be replace together.
    """

    def __init__(self, path, decorate=True, return_value=None):
        if decorate and return_value:
            raise ValueError('Argument return_value %(return_value)s can only '
                             'be used when decorate %(decorate) is False' % {
                                 'return_value': return_value,
                                 'decorate': decorate,
                             })

        self.path = path
        self.decorate = decorate
        self.return_value = return_value

    @staticmethod
    def _locate_method(path):
        path, _sep, method_name = path.rpartition('.')

        # middle paths between module path and method name
        middle_paths = []

        # locate module path
        while True:
            try:
                __import__(path)
                break
            except ImportError:
                pass
            path, _sep, token = path.rpartition('.')
            middle_paths.append(token)
        # import module
        __import__(path)

        middle_paths.reverse()
        parent = sys.modules[path]
        for token in middle_paths:
            parent = getattr(parent, token)

        # parent can be either module or class, or nested class
        return parent, method_name

    @staticmethod
    def _replace_method(parent, method_name, new_method):
        original_method = getattr(parent, method_name)
        setattr(parent, method_name, new_method)
        return original_method

    def _patch(self):
        trace = {
            'args': None,
            'kwargs': None,
            'return_value': None
        }

        def _decorator(*args, **kwargs):
            trace['args'] = args
            trace['kwargs'] = kwargs
            if self.decorate:
                trace['return_value'] = self.original_method(*args, **kwargs)
            else:
                trace['return_value'] = self.return_value
            return trace['return_value']

        self.parent, self.method_name = self._locate_method(self.path)
        self.original_method = self._replace_method(
            self.parent, self.method_name, _decorator)
        return trace

    def _patch_back(self):
        self._replace_method(self.parent, self.method_name, self.original_method)

    def __enter__(self):
        return self._patch()

    def __exit__(self, type, value, traceback):
        self._patch_back()


