# -*- coding: utf-8 -*-
import unittest

from ..future import FutureSourcePair
from ..future.compat import Raise

#------------------------------------------------------------------------------#
# Future Source Tests                                                          #
#------------------------------------------------------------------------------#
class FutureSourcePairTest (unittest.TestCase):
    def test_normal (self):
        results = []
        future, source = FutureSourcePair ()

        self.assertFalse (future.IsCompleted ())

        # continue
        future.Continue     (lambda r, e: results.append ((r, e)))
        future.ContinueSafe (lambda r, e: results.append ((r, e)))
        future_with  = future.ContinueWith (lambda *_: 'done')
        future_error = future.ContinueWith (lambda *_: Raise (ValueError, ValueError ()))

        self.assertEqual (results, [])
        self.assertFalse (future_with.IsCompleted ())
        self.assertFalse (future_error.IsCompleted ())

        # resolve
        source.SetResult (1)

        self.assertEqual (results, [(1, None)] * 2)
        self.assertEqual (future_with.Result (), 'done')
        with self.assertRaises (ValueError):
            future_error.Result ()

        # continue completed
        del results [:]
        future.Continue (lambda r, e: results.append ((r, e)))
        future.ContinueSafe (lambda r, e: results.append ((r, e)))
        future_with = future.ContinueWith (lambda *_: 'done')

        self.assertEqual (results, [(1, None)] * 2)
        self.assertEqual (future_with.Result (), 'done')

    def test_error (self):
        results = []
        future, source = FutureSourcePair ()

        self.assertFalse (future.IsCompleted ())

        # continue
        future.Continue     (lambda r, e: results.append ((r, e)))
        future.ContinueSafe (lambda r, e: results.append ((r, e)))
        future_with = future.ContinueWith (lambda *_: 'done')

        self.assertFalse (future_with.IsCompleted ())
        self.assertEqual (results, [])

        # resolve
        source.SetException (RuntimeError ())

        self.assertEqual (results, [(None, future.Error ())] * 2)
        self.assertEqual (future_with.Result (), 'done')
        with self.assertRaises (RuntimeError):
            future.Result ()

        # continue completed
        del results [:]
        future.Continue (lambda r, e: results.append ((r, e)))
        future.ContinueSafe (lambda r, e: results.append ((r, e)))
        future_with = future.ContinueWith (lambda *_: 'done')

        self.assertEqual (results, [(None, future.Error ())] * 2)
        self.assertEqual (future_with.Result (), 'done')

# vim: nu ft=python columns=120 :
