# -*- coding: utf-8 -*-
from . import future, async, limit, core

from .future import *
from .async  import *
from .limit  import *
from .core   import *

__all__ = future.__all__ + async.__all__ + limit.__all__ + core.__all__

#------------------------------------------------------------------------------#
# Coroutine                                                                    #
#------------------------------------------------------------------------------#
try:
    from . import coroutine
    from .coroutine import *
    __all__ += coroutine.__all__
except ImportError:
    pass

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
