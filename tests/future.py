# -*- coding: utf-8 -*-
import unittest

from ..future import Future, FutureSourcePair

__all__ = ('FutureTest',)
#------------------------------------------------------------------------------#
# Future Test                                                                  #
#------------------------------------------------------------------------------#
class FutureTest (unittest.TestCase):
    """Future unit tests
    """

    def test_abstract (self):
        """Test abstractness
        """
        with self.assertRaises (TypeError):
            Future ()

    def test_all (self):
        """Test Future.All() composition
        """
        # result
        p0, p1 = FutureSourcePair (), FutureSourcePair ()
        future_all = Future.All ((p0 [0], p1 [0]))
        self.assertFalse (future_all.IsCompleted ())

        p1 [1].SetResult (1)
        self.assertFalse (future_all.IsCompleted ())

        p0 [1].SetResult (0)
        self.assertTrue (future_all.IsCompleted ())
        self.assertEqual (future_all.Result (), None)

        # error
        p0, p1 = FutureSourcePair (), FutureSourcePair ()
        future_all = Future.All ((p0 [0], p1 [0]))
        self.assertFalse (future_all.IsCompleted ())

        p1 [1].SetException (ValueError ())
        self.assertTrue (future_all.IsCompleted ())
        with self.assertRaises (ValueError):
            future_all.Result ()

    def test_any (self):
        """Test Future.Any() composition
        """
        # result
        p0, p1 = FutureSourcePair (), FutureSourcePair ()
        future_any = Future.Any ((p0 [0], p1 [0]))
        self.assertFalse (future_any.IsCompleted ())

        p1 [1].SetResult (1)
        self.assertTrue (future_any.IsCompleted ())
        self.assertEqual (future_any.Result (), p1 [0])

        # error
        p0, p1 = FutureSourcePair (), FutureSourcePair ()
        future_any = Future.Any ((p0 [0], p1 [0]))
        self.assertFalse (future_any.IsCompleted ())

        p1 [1].SetException (ValueError ())
        self.assertTrue (future_any.IsCompleted ())
        self.assertEqual (future_any.Result (), p1 [0])

# vim: nu ft=python columns=120 :