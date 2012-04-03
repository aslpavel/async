# -*- coding: utf-8 -*-
from ..future import *
from ..wait import *
from ..cancel import *
from ..async import *

__all__ = ('AnyFuture', 'AllFuture')
#------------------------------------------------------------------------------#
# Any Future                                                                   #
#------------------------------------------------------------------------------#
def AnyFuture (*futures):
    any_future = Future (CompositeWait (*(future.Wait for future in futures)),
        Cancel (lambda: any_future.ErrorRaise (FutureCanceled ())))
    def continuation (future):
        if not any_future.IsCompleted ():
            error = future.Error ()
            if error is None:
                any_future.ResultSet (future.Result ())
            else:
                any_future.ErrorSet (error)
    for future in futures:
        future.Continue (continuation)
    return any_future

#------------------------------------------------------------------------------#
# All Future                                                                   #
#------------------------------------------------------------------------------#
@Async
def AllFuture (*futures):
    for future in futures:
        yield future

# vim: nu ft=python columns=120 :
