# -*- coding: utf-8 -*-
import math
import unittest
import operator

from .. import *
from .common import *

__all__ = ('SinkTest',)
#------------------------------------------------------------------------------#
# Sink Tests                                                                   #
#------------------------------------------------------------------------------#
Count = 1024
class SinkTest (unittest.TestCase):
    def test (self):
        # init
        timer = ManualTimer ()
        sleep_sink_10 = Sink (timer.Sleep, 10)

        # condition
        context = [True]

        # call
        (AllFuture (sleep_sink_10 (1) for i in range (Count))
            .Continue (lambda future: operator.setitem (context, 0, False)))

        # run
        for i in range (Count):
            if not context [0]:
                break
            timer.Tick ()

        self.assertEqual (timer.Time, math.ceil (Count / 10.0))

# vim: nu ft=python columns=120 :
