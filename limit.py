# -*- coding: utf-8 -*-
import sys
from collections import deque

from .async  import Async
from .future import FutureSource

__all__ = ('LimitAsync',)
#------------------------------------------------------------------------------#
# Limit Asynchronous Function                                                  #
#------------------------------------------------------------------------------#
def LimitAsync (limit):
    idle = [limit]

    # decorator
    def decorator (async):
        queue = deque ()

        # worker
        @Async
        def worker ():
            idle [0] -= 1
            try:
                while queue:
                    source, args, keys = queue.popleft ()
                    if not source.Future.IsCompleted ():
                        try:
                            source.ResultSet ((yield async (*args, **keys)))
                        except Exception:
                            source.ErrorSet (sys.exc_info ())
            finally:
                idle [0] += 1

        # limitied version of the async
        def async_limit (*args, **keys):
            source = FutureSource ()
            queue.append ((source, args, keys))

            # fire worker
            if idle [0] > 0: worker ()

            return source.Future

        async_limit.__name__ = async.__name__
        return async_limit

    return decorator

# vim: nu ft=python columns=120 :
