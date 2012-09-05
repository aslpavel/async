# -*- coding: utf-8 -*-
from . import future, source, async, delegate, lazy, scope, core

from .future   import *
from .source   import *
from .async    import *
from .delegate import *
from .lazy     import *
from .scope    import *
from .progress import *
from .core     import *

__all__ = (future.__all__ + source.__all__ + async.__all__ +
           delegate.__all__ + lazy.__all__ + scope.__all__ + progress.__all__ +
           core.__all__)

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
