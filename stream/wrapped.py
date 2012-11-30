# -*- coding: utf-8 -*-
from .stream import Stream
from ..async import Async, AsyncReturn

__all__ = ('WrappedStream',)
#------------------------------------------------------------------------------#
# Wrapped Stream                                                               #
#------------------------------------------------------------------------------#
class WrappedStream (Stream):
    """Wrapped Stream base class
    """
    def __init__ (self, base):
        Stream.__init__ (self)
        self.base = base

    #--------------------------------------------------------------------------#
    # Base stream                                                              #
    #--------------------------------------------------------------------------#
    @property
    def Base (self):
        return self.base

    def __getattr__ (self, name):
        """Access not overridden base stream attributes
        """
        try:
            return getattr (self.base, name)
        except AttributeError: pass

        raise AttributeError ('Underlying stream object {} ,does not have `{}` attribute'
            .format (self.base, name))

    #--------------------------------------------------------------------------#
    # Detach                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Detach (self, cancel = None):
        """Detach underlying base stream
        """
        if self.Disposed:
            raise ValueError ('Stream is disposed')

        try:
            yield self.Flush (cancel)
        finally:
            base, self.base = self.base, None
            yield Stream.Dispose (self, cancel)

        AsyncReturn (base)

    #--------------------------------------------------------------------------#
    # Read                                                                     #
    #--------------------------------------------------------------------------#
    @Async
    def Read (self, size, cancel = None):
        """Asynchronously read data
        """
        with self.reading:
            AsyncReturn ((yield self.base.Read (size, cancel)))

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    @Async
    def Write (self, data, cancel = None):
        """Asynchronously write data
        """
        with self.writing:
            AsyncReturn ((yield self.base.Write (data, cancel)))

    #--------------------------------------------------------------------------#
    # Flush                                                                    #
    #--------------------------------------------------------------------------#
    @Async
    def Flush (self, cancel = None):
        if self.base is None:
            return # base stream was detached

        with self.flushing:
            AsyncReturn ((yield self.base.Flush (cancel)))

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Dispose (self, cancel = None):
        """Dispose object
        """
        if self.Disposed:
            return

        try:
            yield Stream.Dispose (self, cancel)
        finally:
            if self.base is not None:
                yield self.base.Dispose (cancel)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
