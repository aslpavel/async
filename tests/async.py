# -*- coding: utf-8 -*-
import sys
import unittest

from ..future import FutureSourcePair
from ..async  import Async, AsyncReturn

__all__ = ('AsyncTests',)
#------------------------------------------------------------------------------#
# Asynchronous Tests                                                           #
#------------------------------------------------------------------------------#
class AsyncTests (unittest.TestCase):
    def test_normal (self):
        p0, p1, p2 = (FutureSourcePair () for i in range (3))
        context = []
        append = context.append

        @Async
        def async ():
            append (0)
            append ((yield p1 [0]))
            append ((yield p0 [0]))
            append ((yield p2 [0]))
            AsyncReturn (4)

        self.assertEqual (context, [])
        result_future = async ()

        self.assertEqual (context, [0])
        self.assertFalse (result_future.IsCompleted ())

        p0 [1].SetResult (1)
        self.assertEqual (context, [0])
        self.assertFalse (result_future.IsCompleted ())

        p1 [1].SetResult (2)
        self.assertEqual (context, [0, 2, 1])
        self.assertFalse (result_future.IsCompleted ())

        p2 [1].SetResult (3)
        self.assertEqual (context, [0, 2, 1, 3])
        self.assertEqual (result_future.Result (), 4)

    def test_error (self):
        p0, p1, p2 = (FutureSourcePair () for i in range (3))
        context = []
        @Async
        def async ():
            # caught exception
            try:
                yield p0 [0]
            except Exception:
                if sys.exc_info () [0] == ValueError:
                    context.append (0)

            context.append ((yield p1 [0]))

            # uncaught exception
            yield p2 [0]

        future = async ()
        self.assertFalse (future.IsCompleted ())

        p0 [1].SetException (ValueError)
        self.assertEqual (context, [0])
        self.assertFalse (future.IsCompleted ())

        p1 [1].SetResult (1)
        self.assertEqual (context, [0, 1])

        p2 [1].SetException (RuntimeError)
        with self.assertRaises (RuntimeError):
            future.Result ()

    def test_recursion_limit (self):
        future, source = FutureSourcePair ()
        limit = sys.getrecursionlimit ()

        @Async
        def async ():
            count = 0
            for i in range (limit * 2):
                count += (yield future)
            AsyncReturn (count)

        result_future = async ().Traceback ('test_recursion_limit')
        self.assertFalse (result_future.IsCompleted ())

        source.SetResult (1)
        self.assertEqual (result_future.Result (), limit * 2)

# vim: nu ft=python columns=120 :
