# -*- coding: utf-8 -*-
import sys
from collections import deque

from ..future import *
from ..async import *

from .decorator import *

__all__ = ('Serialize',)
#------------------------------------------------------------------------------#
# Serialize                                                                    #
#------------------------------------------------------------------------------#
class Serialize (Decorator):
    """Serialize calls to asynchronous function"""
    def __init__ (self, async):
        self.async, self.uid = async, 0
        self.queue, self.worker, self.wait = deque (), None, None

    def __call__ (self, *args, **keys):
        if self.worker is None:
            self.wait = self.async (*args, **keys)
            if self.wait.IsCompleted ():
                result, self.wait = self.wait, None
                return result

        uid, self.uid = self.uid, self.uid + 1
        future = Future (lambda: self.wait_uid (uid))

        if self.worker is None:
            self.worker = self.worker_run (future)
        else:
            self.queue.append ((uid, future, args, keys))

        return future

    @Async
    def worker_run (self, future):
        try: future.ResultSet ((yield self.wait))
        except Exception: future.ErrorSet (sys.exc_info ())

        try:
            while self.queue:
                uid, future, args, keys = self.queue.popleft ()
                try:
                    self.wait = self.async (*args, **keys)
                    future.ResultSet ((yield self.wait))
                except Exception: future.ErrorSet (sys.exc_info ())
        finally:
            self.wait, self.worker = None, None

    def wait_uid (self, uid):
        uid += 1
        while len (self.queue):
            if self.queue [0][0] > uid:
                return
            if self.wait is None:
                return
            self.wait.Wait ()

        if self.wait is not None:
            self.wait.Wait ()

# vim: nu ft=python columns=120:
