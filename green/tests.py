# -*- coding: utf-8 -*-
import unittest
from .green import GreenAsync, GreenAwait, GreenError
from ..future import FutureSource

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
        coro, source = self.create ()

        future = coro ()
        self.assertFalse (future.IsCompleted ())

        source.ResultSet ('result')
        self.assertTrue (future.IsCompleted ())
        self.assertEqual (future.Result (), 'result')

        self.assertEqual (coro ().Result (), 'result')

    def testFailure (self):
        """Test unsuccessfully resolved coroutine
        """
        coro, source = self.create ()

        with self.assertRaises (GreenError):
            GreenAwait (source.Future)

        future = coro ()
        self.assertFalse (future.IsCompleted ())

        source.ErrorRaise (CoroutineTestError ('error'))
        self.assertTrue (future.IsCompleted ())
        with self.assertRaises (CoroutineTestError):
            future.Result ()

        with self.assertRaises (CoroutineTestError):
            coro ().Result ()

    def create (self):
        """Create (coroutine, source) pair
        """
        source = FutureSource ()

        @GreenAsync
        def coroutine ():
            """Nested coroutine
            """
            return (lambda: GreenAwait (source.Future)) ()

        return coroutine, source

# vim: nu ft=python columns=120 :
