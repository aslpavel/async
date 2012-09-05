# -*- coding: utf-8 -*-
from .async import Async
from .delegate import DelegatedFuture

try:
    from ..event import Event

    __all__ = ('ProgressFuture', 'ProgressAsync',)
    #--------------------------------------------------------------------------#
    # Progress Future                                                          #
    #--------------------------------------------------------------------------#
    class ProgressFuture (DelegatedFuture):
        __slots__ = ('Future', 'OnReport',)

        def __init__ (self, future = None):
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
        return progress_async

except ValueError:
    # async is used outside of pretzel
    __all__ = tuple ()

# vim: nu ft=python columns=120 :
