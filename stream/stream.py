# -*- coding: utf-8 -*-
from ..async import Async
from ..future import RaisedFuture, SucceededFuture

__all__ = ('Stream',)
#------------------------------------------------------------------------------#
# Stream                                                                       #
#------------------------------------------------------------------------------#
class Stream (object):
    """Abstract asynchronous stream
    """
    def __init__ (self):
        self.disposed = False

    #--------------------------------------------------------------------------#
    # Read                                                                     #
    #--------------------------------------------------------------------------#
    def Read (self, size, cancel = None):
        """Asynchronously read data

        Length or returned data is in range [1..size].
        """
        return RaisedFuture (NotImplementedError ())

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    def Write (self, data, cancel = None):
        """Asynchronously write data

        Returns size of written data.
        """
        return RaisedFuture (NotImplementedError ())

    #--------------------------------------------------------------------------#
    # Flush                                                                    #
    #--------------------------------------------------------------------------#
    def Flush (self):
        """Flush stream content
        """
        return SucceededFuture (None)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def IsDisposed (self):
        """Is stream disposed
        """
        return self.disposed

    @Async
    def Dispose (self):
        """Dispose stream
        """
        disposed, self.disposed = self.disposed, True
        if disposed:
            return

        yield self.Flush ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
