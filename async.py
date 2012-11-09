# -*- coding: utf-8 -*-
import sys
import inspect

from .future.future import Future, SucceededFuture, FailedFuture
from .future.source import FutureSource

__all__ = ('Async', 'AsyncReturn', 'DummyAsync',)
#------------------------------------------------------------------------------#
# Asynchronous Function                                                        #
#------------------------------------------------------------------------------#
def AsyncReturn (value):
    """Return value inside asynchronous function
    """
    raise StopIteration (value)

def Async (function):
    """Asynchronous function

    Create asynchronous function out of the generator function. When
    asynchronous function is called generator is created and started. Generator
    must yield only future objects, when such future object is resolved, the
    generator is continued with result of this future. First argument if any of
    StopIteration exception is used as result of asynchronous function,
    otherwise None is used.
    """
    if not inspect.isgeneratorfunction (function):
        raise ValueError ('Function is not a generator')

    def generator_async (*args, **keys):
        generator = function (*args, **keys)
        source    = FutureSource ()

        def continuation (result, error):
            """Resume generator with provided result, error pair.
            """
            try:
                while True:
                    future = (generator.send  (result) if error is None else
                              generator.throw (*error))

                    if not isinstance (future, Future):
                        raise ValueError ('Generator yielded not a Future type: {}'
                            .format (type (future)))

                    elif future.IsCompleted ():
                        # avoid recursion
                        error  = future.Error ()
                        if error is None:
                            result = future.Result ()
                        else:
                            result = None

                    else:
                        future.Continue (continuation)
                        return

            except StopIteration as result:
                source.ResultSet (result.args [0] if result.args else None)
            except Exception:
                source.ErrorSet (sys.exc_info ())

        continuation (None, None)
        return source.Future

    generator_async.__name__ = function.__name__
    generator_async.__doc__  = function.__doc__
    return generator_async

#------------------------------------------------------------------------------#
# Dummy Asynchronous Function                                                  #
#------------------------------------------------------------------------------#
def DummyAsync (function):
    """Dummy asynchronous function

    Create pseudo asynchronous function out of passed function
    """
    def dummy_async (*args, **keys):
        try:
            return SucceededFuture (function (*args, **keys))
        except Exception:
            return FailedFuture (sys.exc_info ())

    dummy_async.__name__ = function.__name__
    dummy_async.__doc__  = function.__doc__
    return dummy_async

# vim: nu ft=python columns=120 :
