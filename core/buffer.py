# -*- coding: utf-8 -*-
from collections import deque

__all__ = ('Buffer',)
#------------------------------------------------------------------------------#
# Buffer                                                                       #
#------------------------------------------------------------------------------#
class Buffer (object):
    """Data buffer

    Used by asynchronous stream.
    """
    def __init__ (self, data = None):
        self.offset = 0
        self.chunks = deque ()
        self.chunks_size = 0

        if data:
            self.Put (data)

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Put (self, data):
        """Put data to buffer
        """
        if data:
            self.chunks.append (data)
            self.chunks_size += len (data)

    def Pop (self, size):
        """Pop data from buffer
        """
        data = self.Peek (size)
        self.Discard (size)
        return data

    def Peek (self, size):
        """Peek "size" bytes for buffer
        """
        data = []
        data_size = 0

        size += self.offset
        while self.chunks:
            if data_size >= size:
                break
            chunk = self.chunks.popleft ()
            data.append (chunk)
            data_size += len (chunk)

        data = b''.join (data)
        self.chunks.appendleft (data)

        return data [self.offset:size]

    def Discard (self, size = None):
        """Discard "size" bytes from buffer
        """
        if size is None:
            self.offset = 0
            self.chunks_size = 0
            self.chunks.clear ()
            return

        if not self.chunks:
            return

        # discard whole chunks
        chunks_size = 0
        size = min (size + self.offset, self.chunks_size)
        while self.chunks:
            if chunks_size > size:
                break
            chunk = self.chunks.popleft ()
            chunks_size += len (chunk)
        self.chunks_size -= chunks_size

        # cut chunk if needed
        offset = len (chunk) - (chunks_size - size)
        if offset << 1 > len (chunk):
            chunk = chunk [offset:]
            self.offset = 0
        else:
            self.offset = offset

        # re-queue chunk
        if chunk:
            self.chunks.appendleft (chunk)
            self.chunks_size += len (chunk)

    def __len__ (self): return self.Length ()
    def Length  (self):
        """Length of the buffer
        """
        return self.chunks_size - self.offset

    def __bool__ (self):
        """Is buffer not empty?
        """
        return bool (self.chunks_size)
    __nonzero__ = __bool__


# vim: nu ft=python columns=120 :
