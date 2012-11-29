# -*- coding: utf-8 -*-
import struct
from collections import deque

from .wrapped import WrappedStream
from ..future import SucceededFuture
from ..async import Async, AsyncReturn
from ..singleton import Singleton
from ..core import BrokenPipeError

__all__ = ('BufferedStream',)
#------------------------------------------------------------------------------#
# Buffered Stream                                                              #
#------------------------------------------------------------------------------#
class BufferedStream (WrappedStream):
    """Buffered stream
    """
    default_buffer_size = 1 << 16

    def __init__ (self, base, buffer_size = None):
        WrappedStream.__init__ (self, base)

        self.read_buffer = Buffer ()
        self.write_buffer = Buffer ()

        self.buffer_size = buffer_size or self.default_buffer_size

    #--------------------------------------------------------------------------#
    # Read                                                                     #
    #--------------------------------------------------------------------------#
    @Async
    def Read (self, size, cancel = None):
        """Read asynchronously at most size and at least one byte(s)
        """
        if not size:
            AsyncReturn (b'')

        with self.reading:
            if not self.read_buffer:
                self.read_buffer.Enqueue ((yield self.base.Read (self.buffer_size, cancel)))

            AsyncReturn (self.read_buffer.Dequeue (size))

    @Async
    def ReadUntilSize (self, size, cancel = None):
        """Read asynchronously exactly size bytes
        """
        if not size:
            AsyncReturn (b'')

        with self.reading:
            while self.read_buffer.Length () < size:
                self.read_buffer.Enqueue ((yield self.base.Read (self.buffer_size, cancel)))

            AsyncReturn (self.read_buffer.Dequeue (size))

    @Async
    def ReadUntilEof (self, cancel = None):
        """Read asynchronously data until stream is closed
        """
        with self.reading:
            try:
                while True:
                    self.read_buffer.Enqueue ((yield self.base.Read (self.buffer_size, cancel)))
            except BrokenPipeError: pass

            AsyncReturn (self.read_buffer.Dequeue ())

    @Async
    def ReadUntilSub (self, sub = None, cancel = None):
        """Read asynchronously until substring is found

        Returns data including substring. Default substring is "\\n".
        """
        sub = sub or b'\n'

        with self.reading:
            offset = 0
            while True:
                data = self.read_buffer.Slice ()
                find_offset = data [offset:].find (sub)
                if find_offset >= 0:
                    break

                offset = max (0, len (data) - len (sub))
                self.read_buffer.Enqueue ((yield self.base.Read (self.buffer_size, cancel)))

            AsyncReturn (self.read_buffer.Dequeue (offset + find_offset + len (sub)))

    @Async
    def ReadUntilRegex (self, regex, cancel = None):
        """Read asynchronously until regular expression is matched

        Returns data (including match) and match object.
        """

        with self.reading:
            while True:
                data = self.read_buffer.Slice ()
                match = regex.search (data)
                if match:
                    break

                self.read_buffer.Enqueue ((yield self.base.Read (self.buffer_size, cancel)))

            AsyncReturn ((self.read_buffer.Dequeue (match.end ()), match))

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    def Write (self, data, cancel = None):
        """Write Bytes to file without blocking
        """
        self.write_buffer.Enqueue (data)
        if not self.flushing and self.write_buffer.Length () >= self.buffer_size:
            self.Flush ()
        return SucceededFuture (len (data))

    #--------------------------------------------------------------------------#
    # Flush                                                                    #
    #--------------------------------------------------------------------------#
    @Singleton
    @Async
    def Flush (self, cancel = None):
        """Flush queued writes asynchronously
        """
        if self.base is None:
            return

        with self.flushing:
            while self.write_buffer:
                self.write_buffer.Dequeue ((yield self.base.Write (
                    self.write_buffer.Slice (self.buffer_size), cancel)), False)
            yield self.base.Flush (cancel)

    #--------------------------------------------------------------------------#
    # Read|Write Tuple                                                         #
    #--------------------------------------------------------------------------#
    tup_struct = struct.Struct ('>I')

    @Async
    def ReadTuple (self, cancel = None):
        """Read Tuple<Bytes> asynchronously
        """
        with self.reading:
            tup_struct_size = self.tup_struct.size

            # count
            while self.read_buffer.Length () < tup_struct_size:
                self.read_buffer.Enqueue ((yield self.base.Read (self.buffer_size, cancel)))
            count = self.tup_struct.unpack (self.read_buffer.Dequeue (tup_struct_size)) [0]

            # sizes
            while self.read_buffer.Length () < tup_struct_size * count:
                self.read_buffer.Enqueue ((yield self.base.Read (self.buffer_size, cancel)))
            size  = 0
            sizes = []
            for _ in range (count):
                sizes.append (self.tup_struct.unpack (self.read_buffer.Dequeue (tup_struct_size)) [0])
                size += sizes [-1]

            # chunks
            while self.read_buffer.Length () < size:
                self.read_buffer.Enqueue ((yield self.base.Read (self.buffer_size, cancel)))
            AsyncReturn (tuple (self.read_buffer.Dequeue (size) for size in sizes))

    @Async
    def WriteTuple (self, tup, cancel = None):
        """Write Tuple<Bytes> to file without blocking
        """
        # count
        yield self.Write (self.tup_struct.pack (len (tup)), cancel)
        # sizes
        for chunk in tup:
            yield self.Write (self.tup_struct.pack (len (chunk)), cancel)
        # chunks
        for chunk in tup:
            yield self.Write (chunk, cancel)

#------------------------------------------------------------------------------#
# Buffer                                                                       #
#------------------------------------------------------------------------------#
class Buffer (object):
    """Bytes FIFO buffer
    """
    def __init__ (self):
        self.offset = 0
        self.chunks = deque ()
        self.chunks_size = 0

    #--------------------------------------------------------------------------#
    # Slice                                                                    #
    #--------------------------------------------------------------------------#
    def Slice (self, size = None, offset = None):
        """Get bytes with "offset" and "size"
        """
        offset = offset or 0
        size = size or self.Length ()

        data = []
        data_size = 0

        # dequeue chunks
        size += self.offset + offset
        while self.chunks:
            if data_size >= size:
                break
            chunk = self.chunks.popleft ()
            data.append (chunk)
            data_size += len (chunk)

        # re-queue merged chunk
        data = b''.join (data)
        self.chunks.appendleft (data)

        return data [self.offset + offset:size]

    #--------------------------------------------------------------------------#
    # Enqueue                                                                  #
    #--------------------------------------------------------------------------#
    def Enqueue (self, data):
        """Enqueue "data" to buffer
        """
        if data:
            self.chunks.append (data)
            self.chunks_size += len (data)

    #--------------------------------------------------------------------------#
    # Dequeue                                                                  #
    #--------------------------------------------------------------------------#
    def Dequeue (self, size = None, returns = None):
        """Dequeue "size" bytes from buffer

        Returns dequeued data if returns if True (or not set) otherwise None.
        """
        size = size or self.Length ()
        if not self.chunks:
            return b''

        data = []
        data_size = 0

        # dequeue chunks
        size = min (size + self.offset, self.chunks_size)
        while self.chunks:
            if data_size >= size:
                break
            chunk = self.chunks.popleft ()
            data.append (chunk)
            data_size += len (chunk)

        if data_size == size:
            # no chunk re-queue
            self.chunks_size -= data_size
            offset, self.offset = self.offset, 0
        else:
            # If offset is beyond the middle of the chunk it will be split
            offset = len (chunk) - (data_size - size)
            if offset << 1 > len (chunk):
                chunk = chunk [offset:]
                offset, self.offset = self.offset, 0
            else:
                offset, self.offset = self.offset, offset

            # re-queue chunk
            self.chunks.appendleft (chunk)
            self.chunks_size += len (chunk) - data_size

        if returns is None or returns:
            return b''.join (data) [offset:size]

    #--------------------------------------------------------------------------#
    # Length                                                                   #
    #--------------------------------------------------------------------------#
    def Length  (self):
        """Length of the buffer
        """
        return self.chunks_size - self.offset
    __len__ = Length

    #--------------------------------------------------------------------------#
    # Empty?                                                                   #
    #--------------------------------------------------------------------------#
    def __bool__ (self):
        """Buffer is not empty
        """
        return bool (self.chunks)
    __nonzero__ = __bool__


# vim: nu ft=python columns=120 :
