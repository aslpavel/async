# -*- coding: utf-8 -*-
import struct
from collections import deque

from .wrapped import WrappedStream
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
        """Read at most size and at least one byte(s)
        """
        if not size:
            AsyncReturn (b'')

        with self.reading:
            if not self.read_buffer:
                self.read_buffer.Enqueue ((yield self.base.Read (self.buffer_size, cancel)))

            AsyncReturn (self.read_buffer.Dequeue (size))

    @Async
    def ReadUntilSize (self, size, cancel = None):
        """Read exactly size bytes
        """
        if not size:
            AsyncReturn (b'')

        with self.reading:
            while self.read_buffer.Length () < size:
                self.read_buffer.Enqueue ((yield self.base.Read (self.buffer_size, cancel)))

            AsyncReturn (self.read_buffer.Dequeue (size))

    @Async
    def ReadUntilEof (self, cancel = None):
        """Read until stream is closed
        """
        with self.reading:
            try:
                while True:
                    self.read_buffer.Enqueue ((yield self.base.Read (self.buffer_size, cancel)))
            except BrokenPipeError: pass

            AsyncReturn (self.read_buffer.Dequeue ())

    @Async
    def ReadUntilSub (self, sub = None, cancel = None):
        """Read until substring is found

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
        """Read until regular expression is matched

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
    @Async
    def Write (self, data, cancel = None):
        """Write data

        Write data without blocking if write buffer's length less then doubled
        buffer size limit, if buffer's length is more then buffer size limit
        flush is started in the background.
        """
        if self.write_buffer.Length () > 2 * self.buffer_size:
            yield self.Flush ()

        with self.writing:
            self.write_buffer.Enqueue (data)
            if not self.flushing and self.write_buffer.Length () >= self.buffer_size:
                self.Flush ()

            AsyncReturn (len (data))

    def WriteBuffer (self, data):
        """Enqueue data to write buffer

        Just enqueues data to write buffer (buffer's size limit would not be
        checked), flush need to be called manually.
        """
        with self.writing:
            self.write_buffer.Enqueue (data)

    #--------------------------------------------------------------------------#
    # Flush                                                                    #
    #--------------------------------------------------------------------------#
    @Singleton
    @Async
    def Flush (self, cancel = None):
        """Flush write buffer

        This function is singleton, which means it will not start new flush
        until previous one is finished (same future object is returned). So it's
        safe to call it regardless to completion of previous call.
        """
        if self.base is None:
            return # base stream was detached

        with self.flushing:
            while self.write_buffer:
                self.write_buffer.Dequeue ((yield self.base.Write (
                    self.write_buffer.Slice (self.buffer_size), cancel)), False)
            yield self.base.Flush (cancel)

    #--------------------------------------------------------------------------#
    # Serialize                                                                #
    #--------------------------------------------------------------------------#
    size_struct = struct.Struct ('>I')

    # Bytes
    @Async
    def BytesRead (self, cancel = None):
        """Read bytes object
        """
        AsyncReturn ((yield self.ReadUntilSize (self.size_struct.unpack
                    ((yield self.ReadUntilSize (self.size_struct.size, cancel))) [0], cancel)))

    def BytesWriteBuffer (self, bytes):
        """Write bytes object to buffer
        """
        self.WriteBuffer (self.size_struct.pack (len (bytes)))
        self.WriteBuffer (bytes)

    # Tuple of structures
    @Async
    def StructTupleRead (self, struct, complex = None, cancel = None):
        """Read tuple of structures
        """
        struct_data = yield self.ReadUntilSize (self.size_struct.unpack ((
                      yield self.ReadUntilSize (self.size_struct.size, cancel))) [0], cancel)
        if complex:
            AsyncReturn (tuple (struct.unpack (struct_data [offset:offset + struct.size])
                for offset in range (0, len (struct_data), struct.size)))
        else:
            AsyncReturn (tuple (struct.unpack (struct_data [offset:offset + struct.size]) [0]
                for offset in range (0, len (struct_data), struct.size)))

    def StructTupleWriteBuffer (self, struct_tuple, struct, complex = None):
        """Write tuple of structures to buffer
        """
        self.WriteBuffer (self.size_struct.pack (len (struct_tuple) * struct.size))
        if complex:
            for struct_target in struct_tuple:
                self.WriteBuffer (struct.pack (*struct_target))
        else:
            for struct_target in struct_tuple:
                self.WriteBuffer (struct.pack (struct_target))

    # Tuple of bytes
    @Async
    def BytesTupleRead (self, cancel = None):
        """Read array of bytes
        """
        bytes_tuple = []
        for size in (yield self.StructTupleRead (self.size_struct, False, cancel)):
            bytes_tuple.append ((yield self.ReadUntilSize (size)))
        AsyncReturn (tuple (bytes_tuple))

    def BytesTupleWriteBuffer (self, bytes_tuple):
        """Write bytes array object to buffer
        """
        self.StructTupleWriteBuffer (tuple (len (bytes) for bytes in bytes_tuple), self.size_struct, False)

        for bytes in bytes_tuple:
            self.WriteBuffer (bytes)

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
        """Get bytes with ``offset`` and ``size``
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

    #--------------------------------------------------------------------------#
    # Representation                                                           #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<Buffer [length:{}] at {}>'.format (self.Length (), id (self))

    def __repr__ (self):
        """String representation
        """
        return str (self)

# vim: nu ft=python columns=120 :
