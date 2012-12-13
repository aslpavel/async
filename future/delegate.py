# -*- coding: utf-8 -*-
from .future import Future

__all__ = ('DelegatedFuture',)
#------------------------------------------------------------------------------#
# Delegated Future                                                             #
#------------------------------------------------------------------------------#
class DelegatedFuture (Future):
    """Delegated future

    Delegate future behavior to different future object.
    """
    __slots__ = Future.__slots__

    #--------------------------------------------------------------------------#
    # Awaiter                                                                  #
    #--------------------------------------------------------------------------#
    def Await (self):
        """Get awaiter
        """
        raise NotImplementedError ()

    def IsCompleted (self):
        return self.Await ().IsCompleted ()

    def OnCompleted (self, continuation):
        self.Await ().OnCompleted (continuation)

    def GetResult (self):
        return self.Await ().GetResult ()

# vim: nu ft=python columns=120 :
