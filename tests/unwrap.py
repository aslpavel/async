# -*- coding: utf-8 -*-
import unittest
from .common import *
from .. import *

__all__ = ('UnwrapTest',)
#------------------------------------------------------------------------------#
# Unwrap Test                                                                  #
#------------------------------------------------------------------------------#
class TestUnwrap (unittest.TestCase):
    def testNromal (self):
        f0, f1 = Future (), Future () # f0 -> f1
        f = f0.Unwrap ()
        self.assertFalse (f.IsCompleted ())

        f0.ResultSet (f1)
        self.assertFalse (f.IsCompleted ())

        f1.ResultSet (10)
        self.assertTrue (f.IsCompleted ())
        self.assertEqual (f.Result (), f1.Result ())

    def testError (self):
        f0 = Future ()
        f = f0.Unwrap ()

        f0.ErrorRaise (ValueError ())
        self.assertEqual (f.Error (), f0.Error ())

        f0, f1 = Future (), Future ()
        f = f0.Unwrap ()
        f0.ResultSet (f1)
        f1.ErrorRaise (TypeError ())
        self.assertEqual (f.Error (), f1.Error ())

    def testWait (self):
        # normal
        f1 = WaitFuture (10)
        f0 = WaitFuture (f1)
        f = f0.Unwrap ()
        self.assertEqual (list (map (bool, (f, f0, f1))), [False, False, False])

        f.Wait ()
        self.assertEqual (list (map (bool, (f, f0, f1))), [True, True, True])
        self.assertEqual (f.Result (), f1.Result ())

        f.Wait () # do nothing

        # error outer
        f0 = WaitFuture (error = ValueError ())
        f = f0.Unwrap ()
        f.Wait ()
        self.assertEqual (f.Error (), f0.Error ())

        # error inner
        f1 = WaitFuture (error = TypeError ())
        f0 = WaitFuture (f1)
        f = f0.Unwrap ()

        f.Wait ()
        self.assertEqual (f.Error (), f1.Error ())

# vim: nu ft=python columns=120 :
