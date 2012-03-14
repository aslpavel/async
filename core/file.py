# -*- coding: utf-8 -*-
import io, os, errno

from .error import *
from ..async import *

__all__ = ('AsyncFile',)
#------------------------------------------------------------------------------#
# Asynchronous File                                                            #
#------------------------------------------------------------------------------#
class AsyncFile (object):
    default_buffer_size = 1 << 16

    def __init__ (self, core, fd, buffer_size = None, closefd = True):
        self.fd = fd
        self.core = core
        self.buffer_size = self.default_buffer_size if buffer_size is None else buffer_size
        self.buffer = io.open (fd, 'rb', buffering = self.buffer_size, closefd = closefd)

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Core (self):
        return self.core

    #--------------------------------------------------------------------------#
    # Reading                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Read (self, size):
        data = self.buffer (size)
        if data is not None:
            AsyncReturn (data)

        try:
            yield self.core.Poll (self.fd, self.core.READABLE)
            AsyncReturn (self.buffer (size))
        except CoreHUPError:
            AsyncReturn (b'')

    @Async
    def ReadExactly (self, size):
        data = io.BytesIO ()
        while data.tell () < size:
            chunk = self.buffer.read (size - data.tell ())
            if chunk is None:
                yield self.core.Poll (self.fd, self.core.READABLE)
            elif len (chunk):
                data.write (chunk)
            else:
                raise EOFError ()
        AsyncReturn (data.getvalue ())

    #--------------------------------------------------------------------------#
    # Writing                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Write (self, data):
        try:
            data = data [os.write (self.fd, data):]
        except OSError as error:
            if error.errno != errno.EAGAIN:
                raise

        while len (data):
            yield self.core.Poll (self.fd, self.core.WRITABLE)
            data = data [os.write (self.fd, data):]

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.buffer.close ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

    def Close (self):
        self.Dispose ()

# vim: nu ft=python columns=120 :
