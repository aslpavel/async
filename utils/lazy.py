# -*- coding: utf-8 -*-
from ..future import *

__all__ = ('LazyFuture',)
#------------------------------------------------------------------------------#
# Lazy Future                                                                  #
#------------------------------------------------------------------------------#
class LazyFuture (BaseFuture):
    __slots__ = BaseFuture.__slots__ + ('future', 'factory',)

    def __init__ (self, factory):
        BaseFuture.__init__ (self)

        self.future = None
        self.factory = factory

    #--------------------------------------------------------------------------#
    # Future Interface                                                         #
    #--------------------------------------------------------------------------#
    def Continue (self, cont):
        return self.futureGet ().Continue (cont)
    def ContinueWithFunction (self, cont):
        return self.futureGet ().ContinueWithFunction (cont)
    def ContinueWithAsync (self, async):
        return self.futureGet ().ContinueWithAsync (async)

    def Result (self):
        return self.futureGet ().Result ()
    def Error (self):
        return self.futureGet ().Error ()
    def IsCompleted (self):
        return self.futureGet ().IsCompleted ()

    @property
    def Wait (self):
        return self.futureGet ().Wait ()

    @property
    def Cancel (self):
        if self.future is None:
            return Cancel ()
        return self.futureGet ().Cancel ()
    
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
