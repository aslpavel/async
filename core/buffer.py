# -*- coding: utf-8 -*-
from collections import deque

__all__ = ('Buffer',)
#------------------------------------------------------------------------------#
# Buffer                                                                       #
#------------------------------------------------------------------------------#
class Buffer (object):
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
        self.chunks_length += len (data)
        self.chunks.append (data)

    def Pick (self, size):
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
        return self.chunks_length - self.offset

    def __bool__ (self):
        return bool (self.chunks)
    __nonzero__ = __bool__


# vim: nu ft=python columns=120 :
