# -*- coding: utf-8 -*-
from .buffer import Buffer
from .error import BrokenPipeError
from ..future import SucceededFuture
from ..async import Async, AsyncReturn, DummyAsync

__all__ = ('AsyncStream',)
#------------------------------------------------------------------------------#
# Asynchronous Stream                                                          #
#------------------------------------------------------------------------------#
class AsyncStream (object):
    """Asynchronous Stream
    """
    default_buffer_size = 1 << 16

    def __init__ (self, buffer_size = None):
        self.buffer_size = buffer_size or self.default_buffer_size

        # read
        self.read_buffer = Buffer ()

        # write
        self.write_coro   = SucceededFuture (None)
        self.write_buffer = Buffer ()

    #--------------------------------------------------------------------------#
    # Read                                                                     #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def ReadRaw (self, size, cancel = None):
        """Unbuffered asynchronous read
        """
        raise NotImplementedError ()

    @Async
    def Read (self, size, cancel = None):
        """Read asynchronously at most size and at least one byte(s)
        """
        if not size:
            AsyncReturn (b'')

        buffer = self.read_buffer
        if not buffer:
            buffer.Put ((yield self.ReadRaw (self.buffer_size, cancel)))

        data = buffer.Peek (size)
        buffer.Discard (size)
        AsyncReturn (data)

    @Async
    def ReadExactly (self, size, cancel = None):
        """Read asynchronously exactly size bytes
        """
        if not size:
            AsyncReturn (b'')

        buffer = self.read_buffer
        while len (buffer) < size:
            buffer.Put ((yield self.ReadRaw (self.buffer_size, cancel)))

        data = buffer.Peek (size)
        buffer.Discard (size)
        AsyncReturn (data)

    @Async
    def ReadAll (self, size, cancel = None):
        """Read asynchronously data until stream is closed
        """
        try:
            while True:
                buffer.Put ((yield self.ReadRaw (self.buffer_size, cancel)))

        except BrokenPipeError:
            if not buffer:
                raise

        data = buffer.Peek (len (buffer))
        buffer.Discard ()
        AsyncReturn (data)

    @Async
    def ReadFind (self, sub = None, cancel = None):
        """Read asynchronously until substring is found

        Returns data including substring.
        """
        sub = sub or b'\n'

        offset = 0
        buffer = self.read_buffer

        while True:
            data = buffer.Peek (len (buffer))
            find_offset = data [offset:].find (sub)
            if find_offset >= 0:
                break

            offset = max (0, len (data) - len (sub))
            buffer.Put ((yield self.ReadRaw (self.buffer_size, cancel)))

        data_size = offset + find_offset + len (sub)
        data = buffer.Peek (data_size)
        buffer.Discard (data_size)
        AsyncReturn (data)

    @Async
    def ReadFindRegex (self, regex, cancel = None):
        """Read asynchronously until regular expression is matched

        Returns data including match.
        """

        buffer = self.read_buffer
        while True:
            data = buffer.Peek (len (buffer))
            match = regex.search (data)
            if match:
                break

            buffer.Put ((yield self.ReadRaw (self.buffer_size, cancel)))

        data_size = match.end ()
        data = buffer.Peek (data_size)
        buffer.Discard (data_size)
        AsyncReturn (data)

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def WriteRaw (self, data):
        """Unbuffered asynchronous write
        """
        raise NotImplementedError ()

    def Write (self, data):
        """Write to file without blocking
        """
        buffer = self.write_buffer
        buffer.Put (data)
        if len (buffer) >= self.buffer_size:
            self.Flush ()

    @Async
    def write_main (self):
        """Write coroutine main function
        """
        buffer = self.write_buffer
        while buffer:
            buffer.Discard ((yield self.WriteRaw (buffer.Peek (self.buffer_size))))

    #--------------------------------------------------------------------------#
    # Flush                                                                    #
    #--------------------------------------------------------------------------#
    def Flush (self):
        """Flush queued writes asynchronously
        """
        if self.write_coro.IsCompleted () and self.write_buffer:
            self.write_coro = self.write_main ()
        return self.write_coro

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def DisposeRaw (self):
        """Dispose underlying asynchronous raw stream
        """

    @Async
    def Dispose (self):
        """Dispose file
        """
        try:
            yield self.Flush ()
        finally:
            self.DisposeRaw ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
