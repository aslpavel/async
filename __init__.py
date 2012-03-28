# -*- coding: utf-8 -*-
from . import async, future, core, utils

from .async import *
from .future import *
from .core import *
from .utils import *

__all__ = async.__all__ + future.__all__ + core.__all__ + utils.__all__
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
