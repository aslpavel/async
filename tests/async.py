# -*- coding: utf-8 -*-
import sys
import unittest

from ..source import FutureSource
from ..async  import Async, AsyncReturn

__all__ = ('AsyncTest',)
#------------------------------------------------------------------------------#
# Async Test                                                                   #
#------------------------------------------------------------------------------#
class AsyncTest (unittest.TestCase):
    def test_normal (self):
        s0, s1, s2 = (FutureSource () for i in range (3))
        context = []
        append = context.append
        @Async
        def async ():
            append (0)
            append ((yield s1.Future))
            append ((yield s0.Future))
            append ((yield s2.Future))
            AsyncReturn (4)

        self.assertEqual (context, [])
        result_future = async ()

        self.assertEqual (context, [0])
        self.assertFalse (result_future.IsCompleted ())

        s0.ResultSet (1)
        self.assertEqual (context, [0])
        self.assertFalse (result_future.IsCompleted ())

        s1.ResultSet (2)
        self.assertEqual (context, [0, 2, 1])
        self.assertFalse (result_future.IsCompleted ())

        s2.ResultSet (3)
        self.assertEqual (context, [0, 2, 1, 3])
        self.assertEqual (result_future.Result (), 4)

    def test_error (self):
        s0, s1, s2 = (FutureSource () for i in range (3))
        context = []
        @Async
        def async ():
            # caught exception
            try:
                yield s0.Future
            except Exception:
                if sys.exc_info () [0] == ValueError:
                    context.append (0)

            context.append ((yield s1.Future))

            # uncaught exception
            yield s2.Future

        future = async ()
        self.assertFalse (future.IsCompleted ())

        s0.ErrorRaise (ValueError)
        self.assertEqual (context, [0])
        self.assertFalse (future.IsCompleted ())

        s1.ResultSet (1)
        self.assertEqual (context, [0, 1])

        s2.ErrorRaise (RuntimeError)
        with self.assertRaises (RuntimeError):
            future.Result ()


    def test_recursion_limit (self):
        source = FutureSource ()
        limit  = sys.getrecursionlimit ()
        @Async
        def async ():
            count = 0
            for i in range (limit * 2):
                count += (yield source.Future)
            AsyncReturn (count)

        future = async ().Traceback ('test_recursion_limit')
        self.assertFalse (future.IsCompleted ())

        source.ResultSet (1)
        self.assertEqual (future.Result (), limit * 2)

# vim: nu ft=python columns=120 :
