# -*- coding: utf-8 -*-
from .source import FutureSource
from .delegate import DelegatedFuture

__all__ = ('ScopeFuture',)
#------------------------------------------------------------------------------#
# ScopeFuture                                                                  #
#------------------------------------------------------------------------------#
class ScopeReturn (BaseException): pass
class ScopeFuture (DelegatedFuture):
    __slots__ = ('source', 'future', 'depth',)

    def __init__ (self):
        self.source = FutureSource ()
        self.depth  = 0

    #--------------------------------------------------------------------------#
    # Future                                                                   #
    #--------------------------------------------------------------------------#
    def FutureGet (self):
        return self.source.Future

    #--------------------------------------------------------------------------#
    # Return                                                                   #
    #--------------------------------------------------------------------------#
    def __call__ (self, result = None):
        self.source.ResultSet (result)
        if self.depth > 0:
            raise ScopeReturn ()

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
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
