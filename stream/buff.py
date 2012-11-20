# -*- coding: utf-8 -*-
from collections import deque

__all__ = ('Buffer',)
#------------------------------------------------------------------------------#
# Buffer                                                                       #
#------------------------------------------------------------------------------#
class Buffer (object):
    """Bytes FIFO buffer

    Used by asynchronous stream.
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
            # cut chunk if offset > chunk.length / 2
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
