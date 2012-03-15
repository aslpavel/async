# -*- coding: utf-8 -*-
import sys

from .future import *

__all__ = ('Async', 'DummyAsync', 'AsyncReturn',)
#------------------------------------------------------------------------------#
# Async                                                                        #
#------------------------------------------------------------------------------#
def Async (function):
    return lambda *args, **keys: CoroutineFuture (function (*args, **keys))

class CoroutineResult (BaseException): pass
def AsyncReturn (value):
    raise CoroutineResult (value)

class CoroutineFuture (Future):
    __slots__ = Future.__slots__ + ('coroutine', )

    def __init__ (self, coroutine):
        Future.__init__ (self)

        self.coroutine = coroutine
        self.wait = None
        self.resume (SucceededFuture (None))

    def Wait (self):
        while self.wait is not None:
            self.wait.Wait ()
        if not self.IsCompleted ():
            raise RuntimeError ('you cann\'t wait inside bound generator')

    def Cancel (self):
        if not self.IsCompleted ():
            if self.wait is None:
                raise FutureCanceled () # we are inside generator
            self.wait.Cancel ()

    def resume (self, future):
        self.wait = None
        result, error = None, None
        try:
            while True:
                future = self.coroutine.send (future.Result ()) if future.Error () is None \
                    else self.coroutine.throw (*future.Error ())

                if not future.IsCompleted ():
                    self.wait = future
                    future.Continue (self.resume)
                    return
        except CoroutineResult as ret:
            result = ret.args [0]
        except StopIteration:
            result = None
        except Exception:
            error = sys.exc_info ()

        self.wait = None
        if error is not None:
            self.ErrorSet (error)
        else:
            self.ResultSet (result)

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
