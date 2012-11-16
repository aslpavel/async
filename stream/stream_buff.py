# -*- coding: utf-8 -*-
import struct

from .buff import Buffer
from .stream import Stream
from ..future import SucceededFuture
from ..async import Async, AsyncReturn
from ..core import BrokenPipeError

__all__ = ('BufferedStream',)
#------------------------------------------------------------------------------#
# Buffered Stream                                                              #
#------------------------------------------------------------------------------#
class BufferedStream (Stream):
    """Buffered stream
    """
    default_buffer_size = 1 << 16

    def __init__ (self, base, buffer_size = None):
        Stream.__init__ (self)

        self.base = base
        self.buffer_size = buffer_size or self.default_buffer_size

        self.flush = SucceededFuture (None)
        self.read_buffer = Buffer ()
        self.write_buffer = Buffer ()

    #--------------------------------------------------------------------------#
    # Base Stream                                                              #
    #--------------------------------------------------------------------------#
    @property
    def Base (self):
        """Underlying base stream
        """
        return self.base

    def __getattr__ (self, name):
        """Access not overridden base stream attributes
        """
        try:
            return getattr (self.base, name)
        except AttributeError: pass

        raise AttributeError ('\'{}\' object has no attribute \'{}\''
            .format (type (self).__name__, name))

    #--------------------------------------------------------------------------#
    # Read                                                                     #
    #--------------------------------------------------------------------------#
    @Async
    def Read (self, size, cancel = None):
        """Read asynchronously at most size and at least one byte(s)
        """
        if not size:
            AsyncReturn (b'')

        buffer = self.read_buffer
        if not buffer:
            buffer.Put ((yield self.base.Read (self.buffer_size, cancel)))

        AsyncReturn (buffer.Pop (size))

    @Async
    def ReadUntilSize (self, size, cancel = None):
        """Read asynchronously exactly size bytes
        """
        if not size:
            AsyncReturn (b'')

        buffer = self.read_buffer
        while len (buffer) < size:
            buffer.Put ((yield self.base.Read (self.buffer_size, cancel)))

        AsyncReturn (buffer.Pop (size))

    @Async
    def ReadUntilEof (self, cancel = None):
        """Read asynchronously data until stream is closed
        """
        buffer = self.read_buffer
        try:
            while True:
                buffer.Put ((yield self.base.Read (self.buffer_size, cancel)))
        except BrokenPipeError: pass

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
            buffer.Put ((yield self.base.Read (self.buffer_size, cancel)))

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

            buffer.Put ((yield self.base.Read (self.buffer_size, cancel)))

        AsyncReturn ((buffer.Pop (match.end ()), match))

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    def Write (self, data, cancel = None):
        """Write Bytes to file without blocking
        """
        buffer = self.write_buffer
        buffer.Put (data)
        if len (buffer) >= self.buffer_size:
            self.Flush ()

    #--------------------------------------------------------------------------#
    # Flush                                                                    #
    #--------------------------------------------------------------------------#
    def Flush (self):
        """Flush queued writes asynchronously
        """
        if self.flush.IsCompleted () and self.write_buffer:
            self.flush = self.flush_main ()
        return self.flush

    @Async
    def flush_main (self):
        """Write coroutine main function
        """
        try:
            buffer = self.write_buffer
            while buffer:
                buffer.Discard ((yield self.base.Write (buffer.Peek (self.buffer_size))))

            yield self.base.Flush ()

        except Exception:
            self.Dispose ()

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Dispose (self):
        """Dispose stream
        """
        if self.disposed:
            return

        try:
            yield Stream.Dispose (self)
        finally:
            self.base.Dispose ()

    #--------------------------------------------------------------------------#
    # Read|Write Tuple                                                         #
    #--------------------------------------------------------------------------#
    tup_struct = struct.Struct ('>I')

    @Async
    def ReadTuple (self, cancel = None):
        """Read Tuple<Bytes> asynchronously
        """
        buffer = self.read_buffer
        tup_struct_size = self.tup_struct.size

        # count
        while len (buffer) < tup_struct_size:
            buffer.Put ((yield self.base.Read (self.buffer_size, cancel)))
        count = self.tup_struct.unpack (buffer.Pop (tup_struct_size)) [0]

        # sizes
        while len (buffer) < tup_struct_size * count:
            buffer.Put ((yield self.base.Read (self.buffer_size, cancel)))
        size  = 0
        sizes = []
        for _ in range (count):
            sizes.append (self.tup_struct.unpack (buffer.Pop (tup_struct_size)) [0])
            size += sizes [-1]

        # chunks
        while len (buffer) < size:
            buffer.Put ((yield self.base.Read (self.buffer_size, cancel)))
        AsyncReturn (tuple (buffer.Pop (size) for size in sizes))

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

# vim: nu ft=python columns=120 :
