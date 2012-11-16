# -*- coding: utf-8 -*-
import sys
import functools
from collections import deque

from .async  import Async
from .future import FutureSource

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
                    source, args, keys = worker_queue.popleft ()
                    if not source.Future.IsCompleted ():
                        try:
                            source.ResultSet ((yield async (*args, **keys)))
                        except Exception:
                            source.ErrorSet (sys.exc_info ())
            finally:
                worker_count [0] -= 1

        def async_limit (*args, **keys):
            source = FutureSource ()
            worker_queue.append ((source, args, keys))

            if worker_count [0] < limit:
                worker ()

            return source.Future

        return functools.update_wrapper (async_limit, async)

    return decorator

# vim: nu ft=python columns=120 :
