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
    any_future = Future (
        CompositeWait (*(future.Wait for future in futures)),
        Cancel (lambda: any_future.ErrorRaise (FutureCanceled ())))

    for future in futures:
        future.Continue (lambda completed_future: any_future.ResultSet (completed_future))
        if any_future.IsCompleted ():
            break

    return any_future

#------------------------------------------------------------------------------#
# All Future                                                                   #
#------------------------------------------------------------------------------#
@Async
def AllFuture (*futures):
    for future in futures:
        yield future

# vim: nu ft=python columns=120 :
