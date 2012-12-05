# -*- coding: utf-8 -*-
from .source import FutureSource
from .delegate import DelegatedFuture

__all__ = ('ScopeFuture',)
#------------------------------------------------------------------------------#
# ScopeFuture                                                                  #
#------------------------------------------------------------------------------#
class ScopeReturn (BaseException): pass
class ScopeFuture (DelegatedFuture):
    """Scope future

    Future is resolved when the last of entered scopes has been left or Return
    method was called.
    """
    __slots__ = DelegatedFuture.__slots__ + ('source', 'future', 'depth',)

    def __init__ (self):
        self.source = FutureSource ()
        self.depth  = 0

    #--------------------------------------------------------------------------#
    # Future                                                                   #
    #--------------------------------------------------------------------------#
    def FutureGet (self):
        """Delegated future interface
        """
        return self.source.Future

    #--------------------------------------------------------------------------#
    # Return                                                                   #
    #--------------------------------------------------------------------------#
    def Return (self, result = None):
        """Resolve this future with provided result
        """
        return self (result)

    def __call__ (self, result = None):
        """Resolve this future with provided result
        """
        self.source.ResultSet (result)
        if self.depth > 0:
            raise ScopeReturn ()

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Resolve this future with None
        """
        self.source.ResultSet (None)

    def __enter__ (self):
        self.depth += 1
        return self

    def __exit__ (self, et, eo, tb):
        self.depth -= 1

        if et == ScopeReturn:
            return True

        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
