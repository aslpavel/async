# -*- coding: utf-8 -*-
import sys

from .source import FutureSource
from .future import SucceededFuture, FailedFuture

__all__ = ('Async', 'AsyncReturn', 'DummyAsync',)
#------------------------------------------------------------------------------#
# Async                                                                        #
#------------------------------------------------------------------------------#
def AsyncReturn (value): raise StopIteration (value)
def Async (function):
    def coroutine_async (*args, **keys):
        coroutine = function (*args, **keys)
        source    = FutureSource ()

        def continuation (future):
            result = None
            error  = None

            try:
                while True:
                    future_error = future.Error ()
                    future = coroutine.send  (future.Result ()) if future_error is None else \
                             coroutine.throw (*future_error)

                    if not future.IsCompleted ():
                        future.Continue (continuation)
                        return

            except StopIteration as ret: result = ret.args [0] if ret.args else None
            except Exception:            error  = sys.exc_info ()

            if error is not None:
                source.ErrorSet (error)
            else:
                source.ResultSet (result)

        continuation (SucceededFuture (None))
        return source.Future

    coroutine_async.__name__ = function.__name__
    return coroutine_async

#------------------------------------------------------------------------------#
# Dummy Async                                                                  #
#------------------------------------------------------------------------------#
def DummyAsync (function):
    def dummy_async (*args, **keys):
        try:
            return SucceededFuture (function (*args, **keys))
        except Exception:
            return FailedFuture (sys.exc_info ())

    dummy_async.__name__ = function.__name__
    return dummy_async

# vim: nu ft=python columns=120 :
