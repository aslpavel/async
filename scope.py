# -*- coding: utf-8 -*-
from .future import Future
from .source import FutureSource

__all__ = ('ScopeFuture',)
#------------------------------------------------------------------------------#
# ScopeFuture                                                                  #
#------------------------------------------------------------------------------#
class ScopeReturn (BaseException): pass
class ScopeFuture (Future):
    __slots__ = ('source', 'future', 'depth',)

    def __init__ (self):
        self.source = FutureSource ()
        self.future = self.source.Future
        self.depth  = 0

    #--------------------------------------------------------------------------#
    # Future Interface                                                         #
    #--------------------------------------------------------------------------#
    def Continue (self, continuation):
        return self.future.Continue (continuation)

    def IsCompleted (self): return self.future.IsCompleted ()
    def Result      (sefl): return self.future.Result ()
    def Error       (self): return self.future.Error ()
    
    #--------------------------------------------------------------------------#
    # Return                                                                   #
    #--------------------------------------------------------------------------#
    def __call__ (self, result):
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

        if et != ScopeReturn:
            self.Dispose ()
            return True
        else:
            return False

# vim: nu ft=python columns=120 :
