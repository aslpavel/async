# -*- coding: utf-8 -*-
import os
import unittest

from ..core.fd import FileBlocking, FileCloseOnExec

__all__ = ('FileOptionsTest',)
#------------------------------------------------------------------------------#
# File Options Test                                                            #
#------------------------------------------------------------------------------#
class FileOptionsTest (unittest.TestCase):
    def testBlocking (self):
        self.setterTest (FileBlocking)

    def testCloseOnExec (self):
        self.setterTest (FileCloseOnExec)

    def setterTest (self, setter):
        try:
            r, w = os.pipe ()

            self.assertEqual (setter (r, True), True)
            self.assertEqual (setter (r), True)

            self.assertEqual (setter (r, False), False)
            self.assertEqual (setter (r), False)

            self.assertEqual (setter (r, True), True)
            self.assertEqual (setter (r), True)

        finally:
            os.close (r)
            os.close (w)

# vim: nu ft=python columns=120 :
