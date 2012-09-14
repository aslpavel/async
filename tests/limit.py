# -*- coding: utf-8 -*-
import math
import operator
import itertools
import unittest
import heapq

from ..limit  import LimitAsync
from ..future import Future, FutureSource

__all__ = ('LimitTest',)
#------------------------------------------------------------------------------#
# Limit Tests                                                                  #
#------------------------------------------------------------------------------#
Count = 1024
class LimitTest (unittest.TestCase):
    def test (self):
        # init
        timer = ManualTimer ()
        sleep_limit_10 = LimitAsync (10) (timer.Sleep)

        # condition
        context = [True]

        # call
        (Future.WhenAll (sleep_limit_10 (1) for i in range (Count))
            .Continue (lambda _: operator.setitem (context, 0, False)))

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
    def __init__ (self):
        self.time  = 0
        self.uid   = itertools.count ()
        self.queue = []

    def Sleep (self, time):
        source = FutureSource ()
        heapq.heappush (self.queue, (self.time + time, next (self.uid), source))
        return source.Future

    def Tick (self):
        self.time += 1
        while self.queue:
            time, uid, source = self.queue [0]

            if source.Future.IsCompleted ():
                heappop (self.queue)
                continue

            if time > self.time:
                return

            heapq.heappop (self.queue)
            source.ResultSet (self.time)

    @property
    def Time (self):
        return self.time

# vim: nu ft=python columns=120 :
