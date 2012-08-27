# -*- coding: utf-8 -*-
import unittest

from ..future import Future

__all__ = ('FutureTest',)
#------------------------------------------------------------------------------#
# Future Test                                                                  #
#------------------------------------------------------------------------------#
class FutureTest (unittest.TestCase):
    def test_abstract (self):
        with self.assertRaises (TypeError):
            Future ()

# vim: nu ft=python columns=120 :
