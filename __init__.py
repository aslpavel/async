# -*- coding: utf-8 -*-
from . import future, async, limit, core, stream, green, event

from .future import *
from .async import *
from .limit import *
from .core import *
from .stream import *
from .green import *
from .event import *

__all__ = (future.__all__ + async.__all__ + limit.__all__ + core.__all__ +
           stream.__all__ + green.__all__ + event.__all__)
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
