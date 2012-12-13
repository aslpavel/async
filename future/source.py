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
    __slots__ = ('Future', 'result', 'error', 'continuations',)

    def __init__ (self):
        self.result  = None
        self.error   = None
        self.continuations = []

        self.Future = SourceFuture (self)

    #--------------------------------------------------------------------------#
    # Resolve                                                                  #
    #--------------------------------------------------------------------------#
    def Resolve (self, future):
        """Resolve embedded future object with provider one
        """
        if future.IsCompleted ():
            error = future.Error ()
            if error is None:
                self.ResultSet (future.Result ())
            else:
                self.ErrorSet (future.Error ())
        else:
            future.Continue (lambda result, error: self.ErrorSet (error)
                if error else  self.ResultSEt (result))

    def ResultSet (self, result):
        """Resolve embedded future object with result
        """
        if self.continuations is None:
            return

        self.result = result
        continuations, self.continuations = self.continuations, None
        for continuation in continuations:
            continuation (self.result, self.error)

    def ErrorSet (self, error):
        """Resolve embedded future object with error
        """
        if self.continuations is None:
            return

        self.error = error
        continuations, self.continuations = self.continuations, None
        for continuation in continuations:
            continuation (self.result, self.error)

    def ErrorRaise (self, exception):
        """Raise exception inside embedded future object
        """
        if self.continuations is None:
            return

        try: raise exception
        except Exception:
            self.error = sys.exc_info ()

        continuations, self.continuations = self.continuations, None
        for continuation in continuations:
            continuation (self.result, self.error)

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
        return self.source.continuations is None

    def OnCompleted (self, continuation):
        if self.source.continuations is None:
            continuation (self.source.result, self.source.error)
        else:
            self.source.continuations.append (continuation)
        return self

    def GetResult (self):
        if self.source.continuations is not None:
            raise FutureNotReady ()
        return self.source.result, self.source.error

# vim: nu ft=python columns=120 :
