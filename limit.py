# -*- coding: utf-8 -*-
import sys
import functools
from collections import deque

from .async  import Async
from .future import FutureSourcePair

__all__ = ('LimitAsync',)
#------------------------------------------------------------------------------#
# Limit Asynchronous Function                                                  #
#------------------------------------------------------------------------------#
def LimitAsync (limit):
    """Limit asynchronous function factory
    """

    def decorator (async):
        """Limit asynchronous function decorator
        """
        worker_count = [0]
        worker_queue = deque ()

        @Async
        def worker ():
            worker_count [0] += 1
            try:
                while worker_queue:
                    future, source, args, keys = worker_queue.popleft ()
                    if not future.IsCompleted ():
                        try:
                            source.SetResult ((yield async (*args, **keys)))
                        except Exception:
                            source.SetError (sys.exc_info ())
            finally:
                worker_count [0] -= 1

        @functools.wraps (async)
        def async_limit (*args, **keys):
            future, source = FutureSourcePair ()
            worker_queue.append ((future, source, args, keys))

            if worker_count [0] < limit:
                worker ()

            return future

        return async_limit

    return decorator

# vim: nu ft=python columns=120 :
