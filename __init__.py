# -*- coding: utf-8 -*-
from . import async, future, source, lazy, core

from .async  import *
from .future import *
from .source import *
from .lazy   import *
from .core   import *

__all__ = async.__all__ + future.__all__ + source.__all__ + lazy.__all__ + core.__all__

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
