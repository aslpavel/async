# -*- coding: utf-8 -*-
from .future import Future

__all__ = ('LazyFuture',)
#------------------------------------------------------------------------------#
# Lazy Future                                                                  #
#------------------------------------------------------------------------------#
class LazyFuture (Future):
    __slots__ = ('future', 'factory',)

    def __init__ (self, factory):
        Future.__init__ (self)

        self.future  = None
        self.factory = factory

    #--------------------------------------------------------------------------#
    # Future Interface                                                         #
    #--------------------------------------------------------------------------#
    def Continue (self, cont):
        return self.futureGet ().Continue (cont)

    def Result (self):      return self.futureGet ().Result ()
    def Error (self):       return self.futureGet ().Error ()
    def IsCompleted (self): return self.futureGet ().IsCompleted ()

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def futureGet (self):
        if self.future is None:
            self.future = self.factory ()
        return self.future

    def __str__ (self):
        return '<LazyFuture: {}>'.format (self.future)

# vim: nu ft=python columns=120 :
