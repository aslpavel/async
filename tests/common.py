# -*- coding: utf-8 -*-
from .. import *

__all__ = ('WaitFuture',)
#------------------------------------------------------------------------------#
# Wait Future                                                                  #
#------------------------------------------------------------------------------#
def WaitFuture (result = None, error = None):
    context = [None]
    def wait ():
        future = context [0]
        if error is None:
            future.ResultSet (result)
        else:
            future.ErrorRaise (error)
    context [0] = Future (wait)

    return context [0]

# vim: nu ft=python columns=120 :
