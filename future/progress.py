# -*- coding: utf-8 -*-
import functools

from .delegate import DelegatedFuture
from ..async import Async

__all__ = ('ProgressFuture', 'ProgressAsync',)
#------------------------------------------------------------------------------#
# Progress Future                                                              #
#------------------------------------------------------------------------------#
class ProgressFuture (DelegatedFuture):
    __slots__ = DelegatedFuture.__slots__ + ('Future', 'OnReport',)

    def __init__ (self, future = None):
        from ..event import Event

        self.Future   = future
        self.OnReport = Event ()

    def Await (self):
        return self.Future

#------------------------------------------------------------------------------#
# Progress Asynchronous Decorator                                              #
#------------------------------------------------------------------------------#
def ProgressAsync (function):
    async = Async (function)

    def progress_async (*args, **keys):
        progress = ProgressFuture ()
        keys ['report'] = progress.OnReport
        progress.Future = ProgressFuture (async (*args, **keys))
        return progress

    return functools.update_wrapper (progress_async, function)

# vim: nu ft=python columns=120 :
