# -*- coding: utf-8 -*-
import sys
import greenlet

from ..future.source import FutureSource

__all__ = ('GreenAsync', 'GreenAwait', 'GreenError',)
#------------------------------------------------------------------------------#
# Greenlet asynchronous function                                               #
#------------------------------------------------------------------------------#
def GreenAsync (function):
    """Greenlet based asynchronous function.

    Create asynchronous function out of provided function.
    """

    def green_async (*args, **keys):
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

    green_async.__name__ = function.__name__
    green_async.__doc__  = function.__doc__
    return green_async

#------------------------------------------------------------------------------#
# Await                                                                        #
#------------------------------------------------------------------------------#
def GreenAwait (future):
    """Await for future to be resolved

    Interrupt current green coroutine (if needed) and continue its execution
    once future object has been resolved. Returns result of the future object.
    """
    if future.IsCompleted ():
        return future.Result ()

    current = greenlet.getcurrent ()
    if not isinstance (current, CoroutineGreenlet):
        raise GreenError ('Await outside of a green function')

    if current.parent is None:
        raise GreenError ('Await without parent')

    return current.parent.switch (future)

#------------------------------------------------------------------------------#
# Green specific types                                                         #
#------------------------------------------------------------------------------#
class CoroutineGreenlet (greenlet.greenlet):
    """Green specific greenlet
    """

class GreenError (Exception):
    """Green specific error
    """

# vim: nu ft=python columns=120 :
