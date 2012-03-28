# -*- coding: utf-8 -*-
from ..async import *
from ..future import *

from collections import deque

__all__ = ('Sink',)
#------------------------------------------------------------------------------#
# Sink                                                                         #
#------------------------------------------------------------------------------#
class Sink (object):
    def __init__ (self, async, limit):
        if limit <= 0:
            raise ValueError ('Limit must be more then zero')

        self.async = async 
        self.idle, self.queue = limit, deque ()

    def __call__ (self, *args, **keys):
        future = Future ()
        self.queue.append ((future, args, keys))

        if self.idle > 0:
            self.worker ()

        return future

    @Async
    def worker (self):
        self.idle -= 1
        try:
            while self.queue:
                future, args, keys = self.queue.popleft ()
                try:
                    future.ResultSet ((yield self.async (*args, **keys)))
                except Exception:
                    future.ErrorSet (sys.exc_info ())
        finally:
            self.idle += 1

# vim: nu ft=python columns=120 :
