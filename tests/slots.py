# -*- coding: utf-8 -*-
import sys
import unittest
from .. import *

__all__ = ('SlotsTest')
#------------------------------------------------------------------------------#
# Slots Tests                                                                  #
#------------------------------------------------------------------------------#
class SlotsTest (unittest.TestCase):
    def testSlots (self):
        # Future
        f = Future ()

        # SucceededFuture
        f_success = SucceededFuture (0)

        # FailedFuture
        try: raise ValueError ()
        except Exception:
            f_error = FailedFuture (sys.exc_info ())

        # UnwrapFuture
        f_unwrap = f.Unwrap ()


        # AsyncFuture
        @Async
        def f_async_ ():
            yield f
        f_async = f_async_ ()

        # Continue with Async
        f_cont_async = f_unwrap.ContinueWithAsync (f_async_)

        futures = (f, f_success, f_error, f_unwrap, f_async, f_cont_async)
        for future in futures:
            with self.assertRaises (AttributeError):
                future.some_not_existing_field = True

# vim: nu ft=python columns=120 :
