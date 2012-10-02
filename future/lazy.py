# -*- coding: utf-8 -*-
from .delegate import DelegatedFuture

__all__ = ('LazyFuture',)
#------------------------------------------------------------------------------#
# Lazy Future                                                                  #
#------------------------------------------------------------------------------#
class LazyFuture (DelegatedFuture):
    """Lazy future

    Future object witch is being delegated only created when first of future
    method is called.
    """
    __slots__ = ('future', 'factory',)

    def __init__ (self, factory):
        self.future  = None
        self.factory = factory

    def FutureGet (self):
        """Create delegated future
        """
        if self.future is None:
            self.future = self.factory ()
        return self.future

    def __str__ (self):
        return '<LazyFuture: {}>'.format (self.future)

# vim: nu ft=python columns=120 :
