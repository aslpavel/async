# -*- coding: utf-8 -*-
from ..future import FutureSource
from ..future.compat import Raise

#------------------------------------------------------------------------------#
# Future Source Tests                                                          #
#------------------------------------------------------------------------------#
import unittest

class FutureSourceTest (unittest.TestCase):
    def test_normal (self):
        results = []
        source  = FutureSource ()
        future  = source.Future

        self.assertFalse (future.IsCompleted ())

        # continue
        future.Then     (lambda r, e: results.append ((r, e)))
        future_with  = future.Chain (lambda *_: 'done')
        future_error = future.Chain (lambda *_: Raise (ValueError, ValueError ()))

        self.assertEqual (results, [])
        self.assertFalse (future_with.IsCompleted ())
        self.assertFalse (future_error.IsCompleted ())

        # resolve
        source.ResultSet (1)

        self.assertEqual (results, [(1, None)])
        self.assertEqual (future_with.Result (), 'done')
        with self.assertRaises (ValueError):
            future_error.Result ()

        # continue completed
        del results [:]
        future.Then (lambda r, e: results.append ((r, e)))
        future_with = future.Chain (lambda *_: 'done')

        self.assertEqual (results, [(1, None)])
        self.assertEqual (future_with.Result (), 'done')

    def test_error (self):
        results = []
        source  = FutureSource ()
        future  = source.Future

        self.assertFalse (future.IsCompleted ())

        # continue
        future.Then (lambda r, e: results.append ((r, e)))
        future_with = future.Chain (lambda *_: 'done')

        self.assertFalse (future_with.IsCompleted ())
        self.assertEqual (results, [])

        # resolve
        source.ErrorRaise (RuntimeError ())

        self.assertEqual (results, [(None, future.Error ())])
        self.assertEqual (future_with.Result (), 'done')
        with self.assertRaises (RuntimeError):
            future.Result ()

        # continue completed
        del results [:]
        future.Then (lambda r, e: results.append ((r, e)))
        future_with = future.Chain (lambda *_: 'done')

        self.assertEqual (results, [(None, future.Error ())])
        self.assertEqual (future_with.Result (), 'done')

# vim: nu ft=python columns=120 :
