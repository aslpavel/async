# -*- coding: utf-8 -*-
from .delegate import DelegatedFuture
from ..async import Async

__all__ = ('ProgressFuture', 'ProgressAsync',)
#--------------------------------------------------------------------------#
# Progress Future                                                          #
#--------------------------------------------------------------------------#
class ProgressFuture (DelegatedFuture):
    __slots__ = ('Future', 'OnReport',)

    def __init__ (self, future = None):
        from ...event import Event

        self.Future   = future
        self.OnReport = Event ()

    #----------------------------------------------------------------------#
    # Future                                                               #
    #----------------------------------------------------------------------#
    def FutureGet (self):
        return self.Future

#--------------------------------------------------------------------------#
# Progress Async Decorator                                                 #
#--------------------------------------------------------------------------#
def ProgressAsync (function):
    async = Async (function)

    def progress_async (*args, **keys):
        progress = ProgressFuture ()
        keys ['report'] = progress.OnReport
        progress.Future = ProgressFuture (async (*args, **keys))
        return progress

    progress_async.__name__ = function.__name__
    progress_async.__doc__  = function.__doc__
    return progress_async

# vim: nu ft=python columns=120 :
