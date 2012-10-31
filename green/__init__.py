# -*- coding: utf-8 -*-
try:
    from . import green
    from .green import *
    __all__ = green.__all__

    #--------------------------------------------------------------------------#
    # Load Test Protocol                                                       #
    #--------------------------------------------------------------------------#
    def load_tests (loader, tests, pattern):
        """Load test protocol
        """
        from unittest import TestSuite
        from . import tests

        suite = TestSuite ()
        for test in (tests,):
            suite.addTests (loader.loadTestsFromModule (test))

        return suite

except ImportError:
    __all__ = ()

# vim: nu ft=python columns=120 :
