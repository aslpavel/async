# -*- coding: utf-8 -*-
from .future import Future

__all__ = ('DelegatedFuture',)
#------------------------------------------------------------------------------#
# Delegated Future                                                             #
#------------------------------------------------------------------------------#
class DelegatedFuture (Future):
    __slots__ = tuple ()

    #--------------------------------------------------------------------------#
    # Future                                                                   #
    #--------------------------------------------------------------------------#
    def FutureGet (self):
        raise NotImplementedError ()

    #--------------------------------------------------------------------------#
    # Future Interface                                                         #
    #--------------------------------------------------------------------------#
    def Continue (self, continuation):
        return self.FutureGet ().Continue (continuation)

    def IsCompleted (self): return self.FutureGet ().IsCompleted ()
    def Result      (self): return self.FutureGet ().Result ()
    def Error       (self): return self.FutureGet ().Error ()

# vim: nu ft=python columns=120 :
