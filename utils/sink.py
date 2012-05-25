# -*- coding: utf-8 -*-
import sys
from collections import deque

from .decorator import *

from ..async import *
from ..future import *
from ..cancel import *
from ..wait import *

__all__ = ('Sink',)
#------------------------------------------------------------------------------#
# Sink                                                                         #
#------------------------------------------------------------------------------#
class Sink (object):
    __slots__ = ('async', 'wait', 'idle', 'queue')

    def __init__ (self, async, limit):
        if limit <= 0:
            raise ValueError ('Limit must be more then zero')

        self.async = async
        self.wait  = CompositeWait ()
        self.idle, self.queue = limit, deque ()

    #--------------------------------------------------------------------------#
    # Call                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self, *args, **keys):
        # future
        future = MutableFuture ()
        future.cancel.Replace (Cancel (lambda: future.ErrorRaise (FutureCanceled ())))
        future.wait.Replace (self.wait)

        # enqueue
        self.queue.append ((future, args, keys))

        # worker
        if self.idle > 0:
            worker = self.worker ()
            self.wait.Add (worker)
            worker.Continue (lambda future: self.wait.Remove (worker.wait))

        return future

    #--------------------------------------------------------------------------#
    # Workers                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def worker (self):
        self.idle -= 1
        try:
            while self.queue:
                future, args, keys = self.queue.popleft ()
                try:
                    if not future.IsCompleted ():
                        async_future = self.async (*args, **keys)
                        future.Replace (async_future)
                        future.ResultSet ((yield async_future))
                except Exception:
                    future.ErrorSet (sys.exc_info ())
        finally:
            self.idle += 1

# vim: nu ft=python columns=120 :
