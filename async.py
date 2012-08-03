# -*- coding: utf-8 -*-
import sys

from .future import *
from .wait import *
from .cancel import *

__all__ = ('Async', 'DummyAsync', 'AsyncReturn',)
#------------------------------------------------------------------------------#
# Async                                                                        #
#------------------------------------------------------------------------------#
def Async (function):
    def async_function (*args, **keys):
        return CoroutineFuture (function (*args, **keys))
    async_function.__name__ = function.__name__
    return async_function

def AsyncReturn (value):
    raise StopIteration (value)

class CoroutineFuture (MutableFuture):
    __slots__  = MutableFuture.__slots__ + ('coroutine', )
    inside_wait   = RaiseWait (FutureError ('Cann\'t wait inside bound generator'))
    inside_cancel = RaiseCancel (FutureCanceled ('Current coroutine future has been canceled'))

    def __init__ (self, coroutine):
        MutableFuture.__init__ (self)

        self.coroutine = coroutine
        self.resume (SucceededFuture (None))

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def resume (self, future):
        self.wait.Replace (self.inside_wait)
        self.cancel.Replace (self.inside_cancel)

        result, error = None, None
        try:
            while True:
                future = self.coroutine.send (future.Result ()) if future.Error () is None \
                    else self.coroutine.throw (*future.Error ())

                if not future.IsCompleted ():
                    self.Replace (future)
                    future.Continue (self.resume)
                    return
        except StopIteration as ret:
            result = ret.args [0] if ret.args else None
        except Exception:
            error = sys.exc_info ()

        self.Replace ()
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
