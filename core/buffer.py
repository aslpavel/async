# -*- coding: utf-8 -*-
from collections import deque

__all__ = ('Buffer',)
#------------------------------------------------------------------------------#
# Buffer                                                                       #
#------------------------------------------------------------------------------#
class Buffer (object):
    """Data buffer

    Used by asynchronous writer.
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
        self.chunks_size += len (data)
        self.chunks.append (data)

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

    def Discard (self, size):
        """Discard "size" bytes from buffer
        """
        chunk = None
        chunks_size = 0

        size += self.offset
        while self.chunks:
            if chunks_size > size:
                break
            chunk = self.chunks.popleft ()
            chunks_size += len (chunk)

        # re-queue last chunk
        if chunk and chunks_size > size:
            chunks_size -= len (chunk)
            self.chunks.appendleft (chunk)

        self.chunks_size -= chunks_size
        self.offset = size - chunks_size if self.chunks else 0

    def __len__ (self): return self.Length ()
    def Length  (self):
        """Length of the buffer
        """
        return self.chunks_size - self.offset

    def __bool__ (self):
        """Is buffer not empty?
        """
        return bool (self.chunks)
    __nonzero__ = __bool__


# vim: nu ft=python columns=120 :
