# -*- coding: utf-8 -*-
import unittest
from .green import GreenAsync, GreenAwait, GreenError
from ..future import FutureSourcePair

__all__ = ('GreenTest',)
#------------------------------------------------------------------------------#
# Green Coroutine Test                                                         #
#------------------------------------------------------------------------------#
class CoroutineTestError (Exception):
    """Error to be used inside coroutine tests
    """

class CoroutineTest (unittest.TestCase):
    """Greenlet based coroutine test
    """

    def testSuccess (self):
        """Test successfully resolved coroutine
        """
        coro, source, _ = self.create ()

        future = coro ()
        self.assertFalse (future.IsCompleted ())

        source.SetResult ('result')
        self.assertTrue (future.IsCompleted ())
        self.assertEqual (future.Result (), 'result')

        self.assertEqual (coro ().Result (), 'result')

    def testFailure (self):
        """Test unsuccessfully resolved coroutine
        """
        coro, source, source_future = self.create ()

        with self.assertRaises (GreenError):
            GreenAwait (source_future)

        future = coro ()
        self.assertFalse (future.IsCompleted ())

        source.SetException (CoroutineTestError ('error'))
        self.assertTrue (future.IsCompleted ())
        with self.assertRaises (CoroutineTestError):
            future.Result ()

        with self.assertRaises (CoroutineTestError):
            coro ().Result ()

    def create (self):
        """Create (coroutine, source) pair
        """
        future, source = FutureSourcePair ()

        @GreenAsync
        def coroutine ():
            """Nested coroutine
            """
            return (lambda: GreenAwait (future)) ()

        return coroutine, source, future

# vim: nu ft=python columns=120 :
