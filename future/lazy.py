# -*- coding: utf-8 -*-
from .delegate import DelegatedFuture

__all__ = ('LazyFuture',)
#------------------------------------------------------------------------------#
# Lazy Future                                                                  #
#------------------------------------------------------------------------------#
class LazyFuture (DelegatedFuture):
    """Lazy future

    Awaiter is initialized lazily, from provided ``awaiter_get`` factory function.
    """
    __slots__ = DelegatedFuture.__slots__ + ('awaiter', 'awaiter_get',)

    def __init__ (self, awaiter_get):
        self.awaiter     = None
        self.awaiter_get = awaiter_get

    #--------------------------------------------------------------------------#
    # Awaitable                                                                #
    #--------------------------------------------------------------------------#
    def Await (self):
        """Get awaiter
        """
        if self.awaiter is None:
            self.awaiter = self.awaiter_get ()
        return self.awaiter

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<{0} [awaiter:{2}] at {1}>'.format (type (self).__name__, id (self), self.awaiter)

# vim: nu ft=python columns=120 :
