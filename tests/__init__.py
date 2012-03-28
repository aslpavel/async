# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------#
# Load Test Protocol                                                           #
#------------------------------------------------------------------------------#
def load_tests (loader, tests, pattern):
    from unittest import TestSuite

    # main
    from . import future
    from . import unwrap
    from . import async
    from . import  slots

    # utils
    from . import serialize
    from . import delegate

    suite = TestSuite ()
    for test in (future, unwrap, async, slots, serialize, delegate):
        suite.addTests (loader.loadTestsFromModule (test))

    return suite
# vim: nu ft=python columns=120 :
