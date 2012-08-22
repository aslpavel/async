# -*- coding: utf-8 -*-
import io
from collections import deque

__all__ = ('Buffer',)
#------------------------------------------------------------------------------#
# Buffer                                                                       #
#------------------------------------------------------------------------------#
class Buffer (object):
    def __init__ (self, data = None):
        self.offset = 0
        self.chunks = deque ()

        if data:
            self.Put (data)

    #--------------------------------------------------------------------------#
    # Methods                                                                  #
    #--------------------------------------------------------------------------#
    def Put (self, data):
        self.chunks.append (data)

    def Get (self, size):
        data   = io.BytesIO ()
        offset = self.offset
        for index in range (len (self.chunks)):
            chunk      = self.chunks [index]
            chunk_size = len (chunk) - offset
            if chunk_size < size:
                data.write (chunk [offset:])
                size  -= chunk_size
                offset = 0
            else:
                data.write (chunk [offset:offset + size])
                break

        return data.getvalue ()

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

        self.offset = size if self.chunks else 0

    #--------------------------------------------------------------------------#
    # Empty                                                                    #
    #--------------------------------------------------------------------------#
    def __bool__ (self):
        return bool (self.chunks)

    __nonzero__ = __bool__

# vim: nu ft=python columns=120 :
