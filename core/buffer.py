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
        self.chunks_length = 0

        if data:
            self.Put (data)

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Put (self, data):
        """Put data to buffer
        """
        self.chunks_length += len (data)
        self.chunks.append (data)

    def Peek (self, size):
        """Peek "size" bytes for buffer
        """
        data   = []
        offset = self.offset
        for index in range (len (self.chunks)):
            chunk      = self.chunks [index]
            chunk_size = len (chunk) - offset
            if chunk_size < size:
                data.append (chunk [offset:])
                size  -= chunk_size
                offset = 0
            else:
                data.append (chunk [offset:offset + size])
                break

        return b''.join (data)

    def Discard (self, size):
        """Discard "size" bytes from buffer
        """
        offset = self.offset
        for index in range (len (self.chunks)):
            chunk      = self.chunks [0]
            chunk_size = len (chunk) - offset
            if chunk_size > size:
                break
            size  -= chunk_size
            offset = 0
            self.chunks.popleft ()
            self.chunks_length -= len (chunk)

        self.offset = offset + size if self.chunks else 0

    def __len__ (self): return self.Length ()
    def Length  (self):
        """Length of the buffer
        """
        return self.chunks_length - self.offset

    def __bool__ (self):
        """Is buffer not empty?
        """
        return bool (self.chunks)
    __nonzero__ = __bool__


# vim: nu ft=python columns=120 :
