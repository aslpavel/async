# -*- coding: utf-8 -*-
import math
import operator
import itertools
import unittest
import heapq

from ..limit  import LimitAsync
from ..future import Future, FutureSourcePair

__all__ = ('LimitTest',)
#------------------------------------------------------------------------------#
# Limit Tests                                                                  #
#------------------------------------------------------------------------------#
Count = 1024
class LimitTest (unittest.TestCase):
    """LimitAsync unit test
    """

    def test (self):
        """LimitAsync test
        """
        # init
        timer = ManualTimer ()
        sleep_limit_10 = LimitAsync (10) (timer.Sleep)

        # condition
        context = [True]

        # call
        (Future.All (sleep_limit_10 (1) for i in range (Count))
            .Then (lambda *_: operator.setitem (context, 0, False)))

        # run
        for i in range (Count):
            if not context [0]:
                break
            timer.Tick ()

        self.assertEqual (timer.Time, math.ceil (Count / 10.0))

#------------------------------------------------------------------------------#
# Manual Timer                                                                 #
#------------------------------------------------------------------------------#
class ManualTimer (object):
    """Asynchronous timer with manual ticks
    """
    def __init__ (self):
        self.time  = 0
        self.uid   = itertools.count ()
        self.queue = []

    def Sleep (self, time):
        """Sleep for "time" ticks
        """
        future, source = FutureSourcePair ()
        heapq.heappush (self.queue, (self.time + time, next (self.uid), source, future))
        return future

    def Tick (self):
        """Increase time by one
        """
        self.time += 1
        while self.queue:
            time, uid, source, future = self.queue [0]

            if future.IsCompleted ():
                heapq.heappop (self.queue)
                continue

            if time > self.time:
                return

            heapq.heappop (self.queue)
            source.SetResult (self.time)

    @property
    def Time (self):
        """Current time
        """
        return self.time

# vim: nu ft=python columns=120 :
