# -*- coding: utf-8 -*-
import sys
import unittest

from .common import *
from ..future import *
from ..async import *
from ..wait import *

__all__ = ('AsyncTest',)
#------------------------------------------------------------------------------#
# Async Tests                                                                  #
#------------------------------------------------------------------------------#
class AsyncTest (unittest.TestCase):
    def testAsyncNormal (self):
        f0, f1, f2 = (Future () for i in range (3))
        context = []
        append = context.append
        @Async
        def async ():
            append (0)
            append ((yield f1))
            append ((yield f0))
            append ((yield f2))
            AsyncReturn (4)

        self.assertEqual (context, [])
        result_future = async ()

        self.assertEqual (context, [0])
        self.assertFalse (result_future.IsCompleted ())

        f0.ResultSet (1)
        self.assertEqual (context, [0])
        self.assertFalse (result_future.IsCompleted ())

        f1.ResultSet (2)
        self.assertEqual (context, [0, 2, 1])
        self.assertFalse (result_future.IsCompleted ())

        f2.ResultSet (3)
        self.assertEqual (context, [0, 2, 1, 3])
        self.assertEqual (result_future.Result (), 4)

    def testAsyncError (self):
        f0, f1, f2 = (Future () for i in range (3))
        context = []
        @Async
        def async ():
            # caught exception
            try:
                yield f0
            except Exception:
                if sys.exc_info () [0] == ValueError:
                    context.append (0)

            context.append ((yield f1))

            # uncaught exception
            yield f2

        result_future = async ()
        self.assertFalse (result_future.IsCompleted ())

        f0.ErrorRaise (ValueError)
        self.assertEqual (context, [0])
        self.assertFalse (result_future.IsCompleted ())

        f1.ResultSet (1)
        self.assertEqual (context, [0, 1])

        f2.ErrorRaise (RuntimeError)
        with self.assertRaises (RuntimeError):
            result_future.Result ()

    def testAsyncRecursionLimit (self):
        future = Future ()
        @Async
        def async ():
            count = 0
            for i in range (sys.getrecursionlimit () * 2):
                count += (yield future)
            AsyncReturn (count)
        result_future = async ()
        self.assertFalse (result_future.IsCompleted ())
        future.ResultSet (1)
        self.assertEqual (result_future.Result (), sys.getrecursionlimit () * 2)

    def testAsyncCancel (self):
        f0, f1 = (CancelableFuture () for i in range (2))
        context = []
        result_future = [None]
        @Async
        def async ():
            try:
                yield f0
            except FutureCanceled:
                context.append (0)
            yield f1
            result_future [0].Cancel ()

        result_future [0] = async () 
        self.assertFalse (result_future [0].IsCompleted ())

        result_future [0].Cancel ()
        self.assertFalse (result_future [0].IsCompleted ())
        self.assertEqual (context, [0])

        f1.ResultSet ('result')
        with self.assertRaises (FutureCanceled):
            result_future [0].Result ()

    def testAsyncWait (self):
        context = []
        def result_setter (result):
            def setter (future):
                context.append (result)
                future.ResultSet (result)
            return setter
        f0, f1, f2 = (self.wait_future (result_setter (i)) for i in range (1, 4))

        @Async
        def async ():
            result = 0
            result += yield f0
            result += yield f1
            result += yield f2
            AsyncReturn (result)

        result_future = async ()
        self.assertFalse (result_future.IsCompleted ())

        result_future.Wait ()
        self.assertEqual (result_future.Result (), 6)
        self.assertEqual (tuple (map (lambda f: f.IsCompleted (), (f0, f1, f2))), (True, True, True))
        self.assertEqual (context, [1, 2, 3])

    def testAsyncWithException (self):
        @Async
        def error ():
            raise ValueError ()
            yield CompletedFuture (1)
        result_future = error ()
        self.assertTrue (result_future.IsCompleted ())
        self.assertEqual (result_future.Error () [0], ValueError)

    def wait_future (self, wait):
        future = Future (Wait (0, lambda uids: wait (future)))
        return future

# vim: nu ft=python columns=120 :
