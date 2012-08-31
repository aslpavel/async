# -*- coding: utf-8 -*-
import sys

from .compat import Raise
from .future import Future, FutureNotReady

__all__ = ('FutureSource',)
#------------------------------------------------------------------------------#
# Future Source                                                                #
#------------------------------------------------------------------------------#
class FutureSource (object):
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
        if future.IsCompleted ():
            error = future.Error ()
            if error is None:
                self.ResultSet (future.Result ())
            else:
                self.ErrorSet (future.Error ())
        else:
            future.Continue (self.Resolve)

    def ResultSet (self, result):
        if self.continuations is None:
            return

        self.result = result
        continuations, self.continuations = self.continuations, None
        for continuation in continuations:
            continuation (self.Future)

    def ErrorSet (self, error):
        if self.continuations is None:
            return

        self.error = error
        continuations, self.continuations = self.continuations, None
        for continuation in continuations:
            continuation (self.Future)

    def ErrorRaise (self, exception):
        if self.continuations is None:
            return

        try: raise exception
        except Exception:
            self.error = sys.exc_info ()

        continuations, self.continuations = self.continuations, None
        for continuation in continuations:
            continuation (self.Future)

#------------------------------------------------------------------------------#
# Source Future                                                                #
#------------------------------------------------------------------------------#
class SourceFuture (Future):
    __slots__ = ('source',)

    def __init__ (self, source):
        self.source = source

    #--------------------------------------------------------------------------#
    # Continuation                                                             #
    #--------------------------------------------------------------------------#
    def Continue (self, continuation):
        if self.source.continuations is None:
            continuation (self)
        else:
            self.source.continuations.append (continuation)

    #--------------------------------------------------------------------------#
    # Result                                                                   #
    #--------------------------------------------------------------------------#
    def Result (self):
        if self.source.continuations is not None:
            raise FutureNotReady ()

        error = self.source.error
        if error is not None:
            Raise (*error)

        return self.source.result

    def Error (self):
        return self.source.error

    def IsCompleted (self):
        return self.source.continuations is None

# vim: nu ft=python columns=120 :
