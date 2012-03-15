# -*- coding: utf-8 -*-
from . import async, core, future, serialize, delegate

from .async import *
from .core import *
from .future import *
from .serialize import *
from .delegate import *

__all__ = (async.__all__ + core.__all__ + future.__all__
    + serialize.__all__ + delegate.__all__)
#------------------------------------------------------------------------------#
# Load Test Protocol                                                           #
#------------------------------------------------------------------------------#
def load_tests (loader, tests, pattern):
    from unittest import TestSuite
    from . import tests

    suite = TestSuite ()
    for test in (tests,):
        suite.addTests (loader.loadTestsFromModule (test))

    return suite
# vim: nu ft=python columns=120 :
