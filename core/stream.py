# -*- coding: utf-8 -*-
import struct

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
    tup_struct = struct.Struct ('>I')
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

        AsyncReturn (buffer.Pop (size))

    @Async
    def ReadUntilSize (self, size, cancel = None):
        """Read asynchronously exactly size bytes
        """
        if not size:
            AsyncReturn (b'')

        buffer = self.read_buffer
        while len (buffer) < size:
            buffer.Put ((yield self.ReadRaw (self.buffer_size, cancel)))

        AsyncReturn (buffer.Pop (size))

    @Async
    def ReadUntilEof (self, cancel = None):
        """Read asynchronously data until stream is closed
        """
        buffer = self.read_buffer
        try:
            while True:
                buffer.Put ((yield self.ReadRaw (self.buffer_size, cancel)))

        except BrokenPipeError:
            if not buffer:
                raise

        AsyncReturn (buffer.Pop (len (buffer)))

    @Async
    def ReadUntilSub (self, sub = None, cancel = None):
        """Read asynchronously until substring is found

        Returns data including substring. Default substring is "\\n".
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

        AsyncReturn (buffer.Pop (offset + find_offset + len (sub)))

    @Async
    def ReadUntilRegex (self, regex, cancel = None):
        """Read asynchronously until regular expression is matched

        Returns data (including match) and match object.
        """

        buffer = self.read_buffer
        while True:
            data = buffer.Peek (len (buffer))
            match = regex.search (data)
            if match:
                break

            buffer.Put ((yield self.ReadRaw (self.buffer_size, cancel)))

        AsyncReturn ((buffer.Pop (match.end ()), match))

    @Async
    def ReadTuple (self, cancel = None):
        """Read Tuple<Bytes> asynchronously
        """
        buffer = self.read_buffer
        tup_struct_size = self.tup_struct.size

        # count
        while len (buffer) < tup_struct_size:
            buffer.Put ((yield self.ReadRaw (self.buffer_size, cancel)))
        count = self.tup_struct.unpack (buffer.Pop (tup_struct_size)) [0]

        # sizes
        while len (buffer) < tup_struct_size * count:
            buffer.Put ((yield self.ReadRaw (self.buffer_size, cancel)))
        size  = 0
        sizes = []
        for _ in range (count):
            sizes.append (self.tup_struct.unpack (buffer.Pop (tup_struct_size)) [0])
            size += sizes [-1]

        # chunks
        while len (buffer) < size:
            buffer.Put ((yield self.ReadRaw (self.buffer_size, cancel)))
        AsyncReturn (tuple (buffer.Pop (size) for size in sizes))

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def WriteRaw (self, data, cancel = None):
        """Unbuffered asynchronous write
        """
        raise NotImplementedError ()

    def Write (self, data):
        """Write Bytes to file without blocking
        """
        buffer = self.write_buffer
        buffer.Put (data)
        if len (buffer) >= self.buffer_size:
            self.Flush ()

    def WriteTuple (self, tup):
        """Write Tuple<Bytes> to file without blocking
        """
        # count
        self.Write (self.tup_struct.pack (len (tup)))
        # sizes
        for chunk in tup:
            self.Write (self.tup_struct.pack (len (chunk)))
        # chunks
        for chunk in tup:
            self.Write (chunk)

    @Async
    def write_main (self):
        """Write coroutine main function
        """
        try:
            buffer = self.write_buffer
            while buffer:
                buffer.Discard ((yield self.WriteRaw (buffer.Peek (self.buffer_size))))

        except Exception:
            self.Dispose ()

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
