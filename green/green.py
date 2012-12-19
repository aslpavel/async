# -*- coding: utf-8 -*-
import sys
import functools
import greenlet

from ..future.pair import FutureSourcePair
from ..future.compat import Raise

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
        future, source = FutureSourcePair ()

        def green_cont (result, error):
            coroutine.parent = greenlet.getcurrent ()

            try:
                value = (coroutine.switch (result) if error is None else
                         coroutine.throw  (*error))

                if coroutine.dead:
                    source.SetResult (value)
                    return

                value.Await ().OnCompleted (green_cont)

            except Exception:
                source.SetError (sys.exc_info ())

        green_cont (None, None)
        return future

    return functools.update_wrapper (green_async, function)

#------------------------------------------------------------------------------#
# Await                                                                        #
#------------------------------------------------------------------------------#
def GreenAwait (awaiter):
    """Await for awaiter to be resolved

    Interrupt current green coroutine (if needed) and continue its execution
    once awaiter object has been resolved. Returns result of the awaiter object.
    """
    if awaiter.IsCompleted ():
        result, error = awaiter.GetResult ()
        if error is None:
            return result
        else:
            Raise (*error)

    current = greenlet.getcurrent ()
    if not isinstance (current, CoroutineGreenlet):
        raise GreenError ('Await outside of a green function')

    if current.parent is None:
        raise GreenError ('Await without parent')

    return current.parent.switch (awaiter)

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
