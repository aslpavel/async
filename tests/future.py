# -*- coding: utf-8 -*-
import unittest

from ..future import Future, FutureSource

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
        s0, s1 = FutureSource (), FutureSource ()
        future_all = Future.All ((s0.Future, s1.Future))
        self.assertFalse (future_all.IsCompleted ())

        s1.ResultSet (1)
        self.assertFalse (future_all.IsCompleted ())

        s0.ResultSet (0)
        self.assertTrue (future_all.IsCompleted ())
        self.assertEqual (future_all.Result (), None)

        # error
        s0, s1 = FutureSource (), FutureSource ()
        future_all = Future.All ((s0.Future, s1.Future))
        self.assertFalse (future_all.IsCompleted ())

        s1.ErrorRaise (ValueError ())
        self.assertTrue (future_all.IsCompleted ())
        with self.assertRaises (ValueError):
            future_all.Result ()

    def test_any (self):
        """Test Future.Any() composition
        """
        # result
        s0, s1 = FutureSource (), FutureSource ()
        future_any = Future.Any ((s0.Future, s1.Future))
        self.assertFalse (future_any.IsCompleted ())

        s1.ResultSet (1)
        self.assertTrue (future_any.IsCompleted ())
        self.assertEqual (future_any.Result (), s1.Future)

        # error
        s0, s1 = FutureSource (), FutureSource ()
        future_any = Future.Any ((s0.Future, s1.Future))
        self.assertFalse (future_any.IsCompleted ())

        s1.ErrorRaise (ValueError ())
        self.assertTrue (future_any.IsCompleted ())
        self.assertEqual (future_any.Result (), s1.Future)

# vim: nu ft=python columns=120 :