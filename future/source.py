# -*- coding: utf-8 -*-
import sys

from .future import Future, FutureNotReady

__all__ = ('FutureSource',)
#------------------------------------------------------------------------------#
# Future Source                                                                #
#------------------------------------------------------------------------------#
class FutureSource (object):
    """Future source

    Embeds future object and controls its stated.
    """
    __slots__ = ('Future', 'result', 'error', 'conts',)

    def __init__ (self):
        self.result  = None
        self.error   = None
        self.conts = []

        self.Future = SourceFuture (self)

    #--------------------------------------------------------------------------#
    # Resolve                                                                  #
    #--------------------------------------------------------------------------#
    def Resolve (self, future):
        """Resolve embedded future object with provider one
        """
        if future.IsCompleted ():
            result, error = future.GetResult ()
            if error is None:
                self.ResultSet (result)
            else:
                self.ErrorSet (error)
        else:
            future.Then (lambda result, error: self.ErrorSet (error)
                if error else  self.ResultSet (result))

    def ResultSet (self, result):
        """Resolve embedded future object with result
        """
        if self.conts is None:
            return

        self.result = result
        conts, self.conts = self.conts, None
        for cont in conts:
            cont (self.result, self.error)

    def ErrorSet (self, error):
        """Resolve embedded future object with error
        """
        if self.conts is None:
            return

        self.error = error
        conts, self.conts = self.conts, None
        for cont in conts:
            cont (self.result, self.error)

    def ErrorRaise (self, exception):
        """Raise exception inside embedded future object
        """
        if self.conts is None:
            return

        try: raise exception
        except Exception:
            self.error = sys.exc_info ()

        conts, self.conts = self.conts, None
        for cont in conts:
            cont (self.result, self.error)

#------------------------------------------------------------------------------#
# Source Future                                                                #
#------------------------------------------------------------------------------#
class SourceFuture (Future):
    """Source future

    Future controlled by its creator FutureSource object.
    """
    __slots__ = Future.__slots__ + ('source',)

    def __init__ (self, source):
        self.source = source

    #--------------------------------------------------------------------------#
    # Awaiter                                                                  #
    #--------------------------------------------------------------------------#
    def IsCompleted (self):
        return self.source.conts is None

    def OnCompleted (self, cont):
        if self.source.conts is None:
            cont (self.source.result, self.source.error)
        else:
            self.source.conts.append (cont)
        return self

    def GetResult (self):
        if self.source.conts is not None:
            raise FutureNotReady ()
        return self.source.result, self.source.error

# vim: nu ft=python columns=120 :
