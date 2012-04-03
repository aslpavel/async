# -*- coding: utf-8 -*-
import unittest
from .. import *
from ..wait import *
from .common import *

__all__ = ('FutureTest',)
#------------------------------------------------------------------------------#
# Future Tests                                                                 #
#------------------------------------------------------------------------------#
class FutureTest (unittest.TestCase):
    #--------------------------------------------------------------------------#
    # Succeeded                                                                #
    #--------------------------------------------------------------------------#
    def testSucceededContinue (self):
        future = Future ()
        future.ResultSet (1)
        self.assertTrue (future.IsCompleted ())
        self.assertEqual (future.Continue (lambda f: f.Result () + 1).Result (), 2)

        with self.assertRaises (FutureError):
            future.Continue (lambda f: None)

    def testSucceededContinueWithFunction (self):
        future = Future ()
        future.ResultSet (1)
        self.assertTrue (future.IsCompleted ())
        self.assertEqual (future.ContinueWithFunction (lambda r: r + 1).Result (), 2)

        with self.assertRaises (FutureError):
            future.ContinueWithFunction (lambda r: None)

    def testSucceededContinueWithAsync (self):
        future, async_future = Future (), Future ()
        future.ResultSet (1)
        def async (result):
            return async_future
        result_future = future.ContinueWithAsync (async)
        self.assertFalse (result_future.IsCompleted ())
        async_future.ResultSet (2)
        self.assertEqual (result_future.Result (), 2)

        with self.assertRaises (FutureError):
            future.ContinueWithAsync (async)

    #--------------------------------------------------------------------------#
    # Failed                                                                   #
    #--------------------------------------------------------------------------#
    def testFailedContinue (self):
        future = Future ()
        future.ErrorRaise (ValueError ())
        self.assertTrue (future.IsCompleted ())
        self.assertTrue (future.Error () is not None)
        with self.assertRaises (ValueError):
            future.Result ()

        executed = [False]
        def cont (f):
            executed [0] = True
            f.Result () + 1
        self.assertEqual (future.Continue (cont).Error () [:2], future.Error () [:2])
        self.assertTrue (executed [0])

        with self.assertRaises (FutureError):
            future.Continue (lambda r: None)

    def testFailedContinueWithFunction (self):
        future = Future ()
        future.ErrorRaise (ValueError ())
        executed = [False]
        def cont (r):
            executed [0] = True
            return r + 1
        self.assertEqual (future.ContinueWithFunction (cont).Error (), future.Error ())
        self.assertFalse (executed [0])

        with self.assertRaises (FutureError):
            future.ContinueWithFunction (lambda r: None)

    def testFailedContinueWithAsync (self):
        future = Future ()
        future.ErrorRaise (ValueError ())
        def async (result):
            return TypeError ()
        self.assertEqual (future.ContinueWithAsync (async).Error (), future.Error ())

        with self.assertRaises (FutureError):
            future.ContinueWithAsync (async)

    #--------------------------------------------------------------------------#
    # Future Continue                                                          #
    #--------------------------------------------------------------------------#
    def testFutureContinue (self):
        future = Future ()
        self.assertFalse (future.IsCompleted ())
        with self.assertRaises (FutureNotReady):
            future.Result ()

        def cont (f):
            self.assertTrue (future.IsCompleted ())
            return f.Result () + 1
        result_future = future.Continue (cont)
        self.assertFalse (result_future.IsCompleted ())

        with self.assertRaises (FutureError):
            future.Continue (cont)

        future.ResultSet (1)
        self.assertEqual (future.Result (), 1)
        self.assertTrue (result_future.IsCompleted ())
        self.assertEqual (result_future.Result (), 2)

    def testFutureErrorContinue (self):
        future = Future ()
        executed = [False]
        def cont (f):
            self.assertTrue (future.IsCompleted ())
            self.assertEqual (future.Error () [0], ValueError)
            executed [0] = True
            return f.Result () + 1
        result_future = future.Continue (cont)
        self.assertFalse (executed [0])

        future.ErrorRaise (ValueError ())
        future.ResultSet (1)
        self.assertEqual (future.result, None)

        self.assertTrue (executed [0])
        with self.assertRaises (ValueError):
            result_future.Result ()

    #--------------------------------------------------------------------------#
    # Future Continue with Function                                            #
    #--------------------------------------------------------------------------#
    def testFutureContinueWithFunction (self):
        future = Future ()
        executed = [False]
        def cont (r):
            executed [0] = True
            return r + 1
        result_future = future.ContinueWithFunction (cont)
        self.assertFalse (result_future.IsCompleted ())
        self.assertFalse (executed [0])

        with self.assertRaises (FutureError):
            future.ContinueWithFunction (cont)

        future.ResultSet (1)
        self.assertTrue (executed [0])
        self.assertTrue (result_future.IsCompleted ())
        self.assertEqual (result_future.Result (), 2)

    def testFutureErrorCotninueWithFunction (self):
        future = Future ()
        executed = [False]
        def cont (r):
            executed [0] = True
            return r + 1
        result_future = future.ContinueWithFunction (cont)

        future.ErrorRaise (ValueError ())
        self.assertTrue (result_future.IsCompleted ())
        self.assertFalse (executed [0])
        self.assertEqual (result_future.Error () [0], ValueError)

    #--------------------------------------------------------------------------#
    # Future Continue with Async                                               #
    #--------------------------------------------------------------------------#
    def testFutureContinueWithAsync (self):
        async_future, future = Future (), Future ()
        def async (r):
            return async_future.Continue (lambda ar: ar.Result () + r)
        result_future = future.ContinueWithAsync (async)
        self.assertFalse (result_future.IsCompleted ())

        with self.assertRaises (FutureError):
            future.ContinueWithAsync (async)

        future.ResultSet (1)
        self.assertFalse (result_future.IsCompleted ())

        async_future.ResultSet (1)
        self.assertTrue (result_future.IsCompleted ())
        self.assertEqual (result_future.Result (), 2)

    def testFutureErrorContinueWithAsync (self):
        async_future, future = Future (), Future ()
        def async (r):
            return async_future.Continue (lambda ar: ar.Result () + r)
        result_future = future.ContinueWithAsync (async)

        future.ErrorRaise (ValueError ())
        self.assertEqual (result_future.Error () [0], ValueError)

    def testFutureWaitContinueWithAsync (self):
        context = []
        future = self.wait_future (result = 3, on_wait = lambda f: context.append (0))
        async_future = self.wait_future (result = 2, on_wait = lambda f: context.append (1))

        def async (r):
            return async_future.ContinueWithFunction (lambda ar: r - ar)
        result_future = future.ContinueWithAsync (async)
        self.assertFalse (result_future.IsCompleted ())

        result_future.Wait ()
        self.assertEqual (future.Result (), 3)
        self.assertEqual (async_future.Result (), 2)
        self.assertEqual (result_future.Result (), 1)
        self.assertEqual (context, [0, 1])

    def testFutureAsyncWaitErrorContinueWithAsync (self):
        context = []
        future = self.wait_future (result = 3, on_wait = lambda f: context.append (0))
        async_future = self.wait_future (error = RuntimeError (), on_wait = lambda f: context.append (1))

        def async (r):
            return async_future.ContinueWithFunction (lambda ar: r - ar)
        result_future = future.ContinueWithAsync (async)
        self.assertFalse (result_future.IsCompleted ())

        result_future.Wait ()
        self.assertEqual (future.Result (), 3)
        self.assertTrue (async_future.Error () [0], RuntimeError)
        self.assertTrue (result_future.Error () [0], RuntimeError)
        self.assertEqual (context, [0, 1])

    def testFutureErrorWaitContinueWithAsync (self):
        context = []
        future = self.wait_future (error = RuntimeError (), on_wait = lambda f: context.append (0))
        async_future = self.wait_future (1, on_wait = lambda f: context.append (1))

        def async (r):
            return async_future.ContinueWithFunction (lambda ar: r - ar)
        result_future = future.ContinueWithAsync (async)
        self.assertFalse (result_future.IsCompleted ())

        result_future.Wait ()
        self.assertEqual (future.Error () [0], RuntimeError)
        self.assertFalse (async_future.IsCompleted (), False)
        self.assertTrue (result_future.Error () [0], RuntimeError)
        self.assertEqual (context, [0])

    def testFutureCancel (self):
        # create cancelable future
        f0 = CancelableFuture ()

        f1 = f0.ContinueWithFunction (lambda f: None)
        f1.ContinueWithFunction (lambda f: None).Cancel ()

        self.assertEqual ((f0.Error () [0], f1.Error () [0]), (FutureCanceled,) * 2)

    def test_wait_future (self):
        with self.assertRaises (ValueError):
            future = self.wait_future (1, 2)

        done = []
        future = self.wait_future (0, on_wait = lambda f: done.append (0))
        self.assertFalse (future.IsCompleted ())
        future.Wait ()
        self.assertTrue (future.IsCompleted ())
        self.assertEqual (future.Result (), 0)
        self.assertEqual (done, [0])

        future = self.wait_future (error = RuntimeError (), on_wait = lambda f: done.append (1))
        self.assertFalse (future.IsCompleted ())
        future.Wait ()
        self.assertTrue (future.IsCompleted ())
        self.assertEqual (future.Error () [0], RuntimeError)
        self.assertEqual (done, [0, 1])

    not_set = object ()
    def wait_future (self, result = not_set, error = not_set, on_wait = None):
        if (error is not self.not_set) and (result is not self.not_set):
            raise ValueError ('only one of result and error is allowed to be set')

        future = [None]
        def wait (uids):
            if error is self.not_set:
                future [0].ResultSet (result)
            else:
                future [0].ErrorRaise (error)
            if on_wait is not None:
                on_wait (future [0])
        future [0] = Future (Wait (-1, wait))
        return future [0]

# vim: nu ft=python columns=120 :
