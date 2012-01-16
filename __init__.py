# -*- coding: utf-8 -*-
from . import async, core

from .async import *
from .core import *

__all__ = async.__all__ + core.__all__
__version__ = async.__version__

# load test protocol
def load_tests (loader, tests, pattern):
    from unittest import TestSuite
    from . import tests
    suite = TestSuite ()
    for test in (tests,):
        suite.addTests (loader.loadTestsFromModule (test))
    return suite
# vim: nu ft=python columns=120 :
