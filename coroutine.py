# -*- coding: utf-8 -*-
import sys
import greenlet

from .future.source import FutureSource

__all__ = ('Coroutine', 'CoroutineAwait', 'CoroutineError',)

class CoroutineError (Exception): pass
class CoroutineGreenlet (greenlet.greenlet): pass
#------------------------------------------------------------------------------#
# Await                                                                        #
#------------------------------------------------------------------------------#
def CoroutineAwait (future):
    """Await for future to be resolved

    Interrupt current coroutine (if needed) and continue its execute once future
    object has been resolved. Returns result of the future object.
    """
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
    """Coroutine

    Create asynchronous function out of provided function.
    """

    def coroutine_async (*args, **keys):
        coroutine = CoroutineGreenlet (lambda _: function (*args, **keys))
        source    = FutureSource ()

        def continuation (result, error):
            coroutine.parent = greenlet.getcurrent ()

            try:
                future = (coroutine.switch (result) if error is None else
                          coroutine.throw  (*error))

                if coroutine.dead:
                    source.ResultSet (future)
                    return

                future.Continue (continuation)

            except Exception:
                source.ErrorSet (sys.exc_info ())

        continuation (None, None)
        return source.Future

    coroutine_async.__name__ = function.__name__
    coroutine_async.__doc__  = function.__doc__
    return coroutine_async

# vim: nu ft=python columns=120 :
