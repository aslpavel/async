# -*- coding: utf-8 -*-
from . import future, async, limit, core, green

from .future import *
from .async  import *
from .limit  import *
from .core   import *
from .green  import *

__all__ = future.__all__ + async.__all__ + limit.__all__ + core.__all__ + green.__all__
#------------------------------------------------------------------------------#
# Load Test Protocol                                                           #
#------------------------------------------------------------------------------#
def load_tests (loader, tests, pattern):
    """Load test protocol
    """
    from unittest import TestSuite
    from . import tests, green

    suite = TestSuite ()
    for test in (tests, green):
        suite.addTests (loader.loadTestsFromModule (test))

    return suite

# vim: nu ft=python columns=120 :
