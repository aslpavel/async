# -*- coding: utf-8 -*-
import sys
import greenlet

from .future.future import SucceededFuture
from .future.source import FutureSource

__all__ = ('Coroutine', 'CoroutineAwait', 'CoroutineError',)

class CoroutineError (Exception): pass
class CoroutineGreenlet (greenlet.greenlet): pass
#------------------------------------------------------------------------------#
# Await                                                                        #
#------------------------------------------------------------------------------#
def CoroutineAwait (future):
    if future.IsCompleted ():
        return future.Result ()

    current = greenlet.getcurrent ()
    if not isinstance (current, CoroutineGreenlet):
        raise CoroutineError ('Await outside of a coroutine')

    if current.parent is None:
        raise CoroutineError ('Await without parent')

    current.parent.switch (future)

#------------------------------------------------------------------------------#
# Coroutine                                                                    #
#------------------------------------------------------------------------------#
def Coroutine (function):
    def coroutine_async (*args, **keys):
        coroutine = CoroutineGreenlet (lambda _: function (*args, **keys))
        source    = FutureSource ()

        def continuation (future):
            coroutine.parent = greenlet.getcurrent ()

            try:
                error  = future.Error ()
                future = coroutine.switch (future.Result ()) if error is None else \
                         coroutine.throw  (*error)

                if coroutine.dead:
                    source.ResultSet (future)
                    return

                future.Continue (continuation)

            except Exception:
                source.ErrorSet (sys.exc_info ())

        continuation (SucceededFuture (None))
        return source.Future

    coroutine_async.__name__ = function.__name__
    coroutine_async.__doc__  = function.__doc__
    return coroutine_async

# vim: nu ft=python columns=120 :
