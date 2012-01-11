# -*- coding: utf-8 -*-
import sys
import unittest
from .async import *

class FutureTest (unittest.TestCase):
    # Succeded
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

    # Failed
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

    # Future Continue
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
    
    # Future Continue with Function
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

    # Future Continue with Async
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
        future = Future ()
        middle_future = (future
            .ContinueWithFunction (lambda r: r + 1)
            .ContinueWithFunction (lambda r: r + 1))
        cancel_future = middle_future.ContinueWithFunction (lambda r: r + 1)
        result_future = cancel_future.ContinueWithFunction (lambda r: r + 1)
        cancel_future.Cancel ()
        self.assertEqual (result_future.Error () [0], FutureCanceled)
        future.ResultSet (1)
        self.assertEqual (middle_future.Result (), 3)

    not_set = object ()
    def wait_future (self, result = not_set, error = not_set, on_wait = None):
        if (error is not self.not_set) and (result is not self.not_set):
            raise ValueError ('only one of result and error is allowed to be set')
            
        future = [None]
        def wait ():
            if error is self.not_set:
                future [0].ResultSet (result)
            else:
                future [0].ErrorRaise (error)
            if on_wait is not None:
                on_wait (future [0])
        future [0] = Future (wait)
        return future [0]

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
        f0, f1 = (Future () for i in range (2))
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
        result_future = error ()
        self.assertTrue (result_future.IsCompleted ())
        self.assertEqual (result_future.Error () [0], ValueError)

    def wait_future (self, wait):
        future = [None]
        def wait_future ():
            wait (future [0])
        future [0] = Future (wait_future)
        return future [0]

class TestSerialize (unittest.TestCase):
    def testNormal (self):
        tester = self.Tester ()
        async, finish = tester.async, tester.finish
        context = []

        for i in range (3):
            async (i).ContinueWithFunction (lambda result: context.append (result))

        self.assertEqual (context, [])
        finish (2, 0) # 2 -> 0
        self.assertEqual (context, [])
        finish (0, 1) # 0 -> 1
        self.assertEqual (context, [1])
        finish (1, 2) # 1 -> 2
        self.assertEqual (context, [1, 2, 0])
        self.assertEqual (async.worker, None)

    def testRestart (self):
        tester = self.Tester ()
        async, finish = tester.async, tester.finish
        context = []

        async (0).ContinueWithFunction (lambda result: context.append (result))
        self.assertEqual (context, [])
        self.assertNotEqual (async.worker, None)
        finish (0, 0)
        self.assertEqual (context, [0])
        self.assertEqual (async.worker, None)

        # restart worker
        async (1).ContinueWithFunction (lambda result: context.append (result))
        self.assertEqual (context, [0])
        finish (1, 1)
        self.assertEqual (context, [0, 1])
        self.assertEqual (async.worker, None)

    def testFinished (self):
        tester = self.Tester ()
        async, finish = tester.async, tester.finish
        context = []

        # finsihed future
        self.assertEqual (async.worker, None)
        finish (0, 0)
        async (0).ContinueWithFunction (lambda result: context.append (result))
        self.assertEqual (context, [0])
        self.assertEqual (async.worker, None)

    class Tester (object):
        def __init__ (self):
            self.futures = {}

        @Serialize
        def async (self, uid):
            future = self.futures.get (uid)
            if future is None:
                future = Future ()
                self.futures [uid] = future
            return future

        def finish (self, uid, result):
            future = self.futures.get (uid)
            if future is None:
                future = SucceededFuture (result)
                self.futures [uid] = future
            else:
                future.ResultSet (result)


if __name__ == '__main__':
    unittest.main ()
# vim: nu ft=python columns=120 :
