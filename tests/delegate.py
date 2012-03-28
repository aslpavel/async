# -*- coding: utf-8 -*-
import unittest
from .common import *
from .. import *

__all__ = ('DelegateTest',)
#------------------------------------------------------------------------------#
# Delegate Tests                                                               #
#------------------------------------------------------------------------------#
class DelegateTest (unittest.TestCase):
    def testSync (self):
        future = WaitFuture (10)
        a = self.A (future)
        self.assertFalse (future)
        self.assertEqual (a.Method (1), 11)
        self.assertTrue  (future)

    def testAsync (self):
        future = WaitFuture (10)
        a = self.A (future)
        self.assertFalse (future)
        a_future = a.Method.Async (1)
        self.assertFalse (future)
        self.assertFalse (a_future)
        future.Wait ()
        self.assertTrue (future)
        self.assertEqual (a_future.Result (), 11)

    class A (object):
        def __init__ (self, future):
            self.future = future

        @Delegate
        @Async
        def Method (self, value):
            AsyncReturn (value + (yield self.future))

# vim: nu ft=python columns=120 :
