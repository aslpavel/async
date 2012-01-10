# -*- coding: utf-8 -*-
from .async import *
from .async import __all__, __version__

# load test protocol
def load_tests (loader, tests, pattern):
    from unittest import TestSuite
    from . import tests
    suite = TestSuite ()
    for test in (tests,):
        suite.addTests (loader.loadTestsFromModule (test))
    return suite
# vim: nu ft=python columns=120 :
