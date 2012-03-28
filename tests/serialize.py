# -*- coding: utf-8 -*-
import unittest
from .. import *

#------------------------------------------------------------------------------#
# Serialize Tests                                                              #
#------------------------------------------------------------------------------#
class SerializeTest (unittest.TestCase):
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

        # finished future
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

# vim: nu ft=python columns=120 :
