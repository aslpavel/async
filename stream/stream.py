# -*- coding: utf-8 -*-
from ..async import Async
from ..future import RaisedFuture, CompletedFuture

__all__ = ('Stream',)
#------------------------------------------------------------------------------#
# Stream                                                                       #
#------------------------------------------------------------------------------#
class Stream (object):
    """Abstract asynchronous stream
    """

    FLAG_NONE       = 0x00
    FLAG_DISPOSING  = 0x01
    FLAG_DISPOSED   = 0x02
    FLAG_READING    = 0x04
    FLAG_WRITING    = 0x08
    FLAG_FLUSHING   = 0x10
    FLAG_ACCEPTING  = 0x20
    FLAG_CONNECTING = 0x40

    def __init__ (self):
        self.flags = self.FLAG_NONE

        self.reading  = StreamContext ('reading',  self, self.FLAG_READING, self.FLAG_DISPOSED)
        self.writing  = StreamContext ('writing',  self, self.FLAG_WRITING, self.FLAG_DISPOSED)
        self.flushing = StreamContext ('flushing', self, self.FLAG_FLUSHING, self.FLAG_DISPOSED)

    #--------------------------------------------------------------------------#
    # Flags                                                                    #
    #--------------------------------------------------------------------------#
    @property
    def Flags (self):
        return self.flags

    @property
    def FlagsNames (self):
        """Return set flags as list of names
        """
        flags = []
        self.flags & self.FLAG_DISPOSING  and flags.append ('disposing')
        self.flags & self.FLAG_DISPOSED   and flags.append ('disposed')
        self.flags & self.FLAG_READING    and flags.append ('reading')
        self.flags & self.FLAG_WRITING    and flags.append ('writing')
        self.flags & self.FLAG_FLUSHING   and flags.append ('flushing')
        self.flags & self.FLAG_CONNECTING and flags.append ('connecting')
        self.flags & self.FLAG_ACCEPTING  and flags.append ('accepting')
        return flags

    #--------------------------------------------------------------------------#
    # Read                                                                     #
    #--------------------------------------------------------------------------#
    @property
    def Reading (self):
        """Is stream being read
        """
        return self.reading

    def Read (self, size, cancel = None):
        """Asynchronously read data

        Length or returned data is in range [1..size].
        """
        return RaisedFuture (NotImplementedError ())

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    @property
    def Writing (self):
        """Is stream being written
        """
        return self.writing

    def Write (self, data, cancel = None):
        """Asynchronously write data

        Returns size of written data.
        """
        return RaisedFuture (NotImplementedError ())

    #--------------------------------------------------------------------------#
    # Flush                                                                    #
    #--------------------------------------------------------------------------#
    @property
    def Flushing (self):
        return self.flushing

    def Flush (self, cancel = None):
        """Flush stream content
        """
        return CompletedFuture (None)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    @property
    def Disposing (self):
        """Is stream disposing
        """
        return self.flags & self.FLAG_DISPOSING

    @property
    def Disposed (self):
        """Is stream disposed
        """
        return self.flags & (self.FLAG_DISPOSING | self.FLAG_DISPOSED)

    @Async
    def Dispose (self, cancel = None):
        """Dispose stream
        """
        if self.Disposed:
            return

        try:
            self.flags ^= self.FLAG_DISPOSING
            yield self.Flush (cancel)
        finally:
            self.flags ^= self.FLAG_DISPOSING | self.FLAG_DISPOSED

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<{} [flags:{}] at {}>'.format (type (self).__name__,
            ','.join (self.FlagsNames), id (self))

    def __repr__ (self):
        """String representation
        """
        return str (self)

#------------------------------------------------------------------------------#
# Stream Context                                                               #
#------------------------------------------------------------------------------#
class StreamContext (object):
    __slots__ = ('name', 'stream', 'active_flag', 'error_flag')

    def __init__ (self, name, stream, active_flag, error_flag):
        self.name = name
        self.stream = stream
        self.active_flag = active_flag
        self.error_flag = active_flag | error_flag

    #--------------------------------------------------------------------------#
    # Enter                                                                    #
    #--------------------------------------------------------------------------#
    def __enter__ (self):
        """Enter context
        """
        if self.stream.flags & self.error_flag:
            if self.stream.flags & self.active_flag:
                raise ValueError ('Stream is already in \'{}\' state'.format (self.name))
            else:
                raise ValueError ('Stream is disposed')
        self.stream.flags |= self.active_flag
        return self

    #--------------------------------------------------------------------------#
    # Leave                                                                    #
    #--------------------------------------------------------------------------#
    def __exit__ (self, et, eo, tb):
        """Leave context
        """
        self.stream.flags ^= self.active_flag
        return False

    #--------------------------------------------------------------------------#
    # Is Active                                                                #
    #--------------------------------------------------------------------------#
    def __bool__ (self):
        """Is context active
        """
        return bool (self.stream.flags & self.active_flag)
    __nonzero__ = __bool__

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """Context string representation
        """
        return '<Context [name:{} active:{}] at {}>'.format (self.name, bool (self), id (self))
    __repr__ = __str__

# vim: nu ft=python columns=120 :
