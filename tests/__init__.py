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

    def test_async (*args):
        core_saved = Core.Instance ()
        try:
            # execute test
            with Core.Instance (Core ()) as core:
                test_future = Async (test) (*args)
                test_future.Continue (lambda *_: core.Dispose ())
                core.Execute ()
            test_future.Result ()

        finally:
            # restore core
            core.Instance (core_saved)

    return functools.update_wrapper (test_async, test)

#------------------------------------------------------------------------------#
# Load Test Protocol                                                           #
#------------------------------------------------------------------------------#
def load_tests (loader, tests, pattern):
    from unittest import TestSuite
    from . import future, source, async, limit, file, buff, stream

    suite = TestSuite ()
    for test in (future, source, async, limit, file, buff, stream):
        suite.addTests (loader.loadTestsFromModule (test))

    return suite

# vim: nu ft=python columns=120 :
