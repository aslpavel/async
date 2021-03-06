# -*- coding: utf-8 -*-
import functools

from .. import Core, Async

__all__ = ('AsyncTest',)
#------------------------------------------------------------------------------#
# Asynchronous Test                                                            #
#------------------------------------------------------------------------------#
def AsyncTest (test):
    """Asynchronous test

    Make asynchronous test from from generator test function.
    """

    @functools.wraps (test)
    def test_async (*args):
        # execute test
        with Core.Instance (Core ()) as core:
            test_future = Async (test) (*args)
            test_future.Then (lambda *_: core.Dispose ())
            if not core.Disposed:
                core ()
        test_future.Result ()

    return test_async

#------------------------------------------------------------------------------#
# Load Test Protocol                                                           #
#------------------------------------------------------------------------------#
def load_tests (loader, tests, pattern):
    from unittest import TestSuite
    from . import future, pair, source, async, limit, file, buffered, event

    suite = TestSuite ()
    for test in (future, pair, source, async, limit, file, buffered, event):
        suite.addTests (loader.loadTestsFromModule (test))

    return suite

# vim: nu ft=python columns=120 :
