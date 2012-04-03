# -*- coding: utf-8 -*-
from heapq import heappush, heappop
from .. import *

from ..cancel import *
from ..wait import *

__all__ = ('WaitFuture', 'CancelableFuture', 'ManualTimer')
#------------------------------------------------------------------------------#
# Wait Future                                                                  #
#------------------------------------------------------------------------------#
def WaitFuture (result = None, error = None):
    def wait (uids):
        if error is None:
            future.ResultSet (result)
        else:
            future.ErrorRaise (error)
    future = Future (wait = Wait (-1, wait))
    return future

#------------------------------------------------------------------------------#
# Cancelable Future                                                            #
#------------------------------------------------------------------------------#
def CancelableFuture ():
    future = Future (cancel = Cancel (lambda: future.ErrorRaise (FutureCanceled ())))
    return future

#------------------------------------------------------------------------------#
# Manual Timer                                                                 #
#------------------------------------------------------------------------------#
class ManualTimer (object):
    def __init__ (self):
        self.time, self.uid = 0, 0
        self.queue = []

    def Sleep (self, time):
        future = Future ()
        self.uid, uid = self.uid + 1, self.uid
        heappush (self.queue, (self.time + time, uid, future))
        return future

    def Tick (self):
        self.time += 1
        while self.queue:
            time, uid, future = self.queue [0]
            if future.IsCompleted ():
                heappop (self.queue)
                continue
            if time > self.time:
                return
            heappop (self.queue)
            future.ResultSet (self.time)

    @property
    def Time (self):
        return self.time

# vim: nu ft=python columns=120 :
