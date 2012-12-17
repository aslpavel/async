# -*- coding: utf-8 -*-
import sys
import inspect
import functools

from .future.future import CompletedFuture
from .future.pair import FutureSourcePair

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
        future, source = FutureSourcePair ()

        def generator_cont (result, error):
            """Resume generator with provided result, error pair.
            """
            try:
                while True:
                    awaiter = (generator.send  (result) if error is None else
                               generator.throw (*error)).Await ()

                    if awaiter.IsCompleted ():
                        result, error = awaiter.GetResult ()
                    else:
                        awaiter.OnCompleted (generator_cont)
                        return

            except StopIteration as result:
                source.SetResult (result.args [0] if result.args else None)
            except Exception:
                source.SetError (sys.exc_info ())

            generator.close ()

        generator_cont (None, None)
        return future

    return functools.update_wrapper (generator_async, function)

#------------------------------------------------------------------------------#
# Dummy Asynchronous Function                                                  #
#------------------------------------------------------------------------------#
def DummyAsync (function):
    """Dummy asynchronous function

    Create pseudo asynchronous function out of passed function
    """
    def dummy_async (*args, **keys):
        try:
            return CompletedFuture (function (*args, **keys))
        except Exception:
            return CompletedFuture (error = sys.exc_info ())

    return functools.update_wrapper (dummy_async, function)

# vim: nu ft=python columns=120 :
