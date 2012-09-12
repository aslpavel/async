# -*- coding: utf-8 -*-
import io
import os
import errno

from .fd      import FileCloseOnExec, FileBlocking
from .core    import Core, CoreDisconnectedError
from .buffer  import Buffer
from ..future import SucceededFuture
from ..async  import Async, AsyncReturn

__all__ = ('AsyncFile',)
#------------------------------------------------------------------------------#
# Asynchronous File                                                            #
#------------------------------------------------------------------------------#
class AsyncFile (object):
    default_buffer_size = 1 << 16

    def __init__ (self, fd, buffer_size = None, closefd = None, core = None):
        self.fd = fd
        self.core = core or Core.Instance ()
        self.buffer_size = buffer_size or self.default_buffer_size

        # read
        self.read_buffer = io.open (fd, 'rb', buffering = self.buffer_size,
            closefd = True if closefd is None else closefd)

        # flush
        self.flusher = SucceededFuture (None)
        self.flusher_buffer = Buffer ()

        self.Blocking (False)

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
    def Read (self, size, cancel = None):
        while True:
            data = self.read_buffer.read (size)
            if data is None:
                try:
                    yield self.core.Poll (self.fd, self.core.READ, cancel)
                except CoreDisconnectedError: pass
            elif data:
                AsyncReturn (data)
            else:
                raise CoreDisconnectedError ()

    def ReadExactly (self, size, cancel = None):
        return (self.ReadExactlyInto (size, io.BytesIO (), cancel)
            .ContinueWithFunction (lambda buffer: buffer.getvalue ()))

    @Async
    def ReadExactlyInto (self, size, stream, cancel = None):
        left = size
        while left:
            data = self.read_buffer.read (left)
            if data is None:
                try:
                    yield self.core.Poll (self.fd, self.core.READ, cancel)
                except CoreDisconnectedError: pass
            elif data:
                stream.write (data)
                left -= len (data)
            else:
                raise CoreDisconnectedError ()
        AsyncReturn (stream)

    #--------------------------------------------------------------------------#
    # Writing                                                                  #
    #--------------------------------------------------------------------------#
    def Write (self, data):
        self.flusher_buffer.Put (data)
        if self.flusher_buffer.Length () >= self.buffer_size:
            self.Flush ()

    #--------------------------------------------------------------------------#
    # Flush                                                                    #
    #--------------------------------------------------------------------------#
    def Flush (self):
        if self.flusher.IsCompleted () and self.flusher_buffer:
            self.flusher = self.flusher_main ()
        return self.flusher

    @Async
    def flusher_main (self):
        buffer = self.flusher_buffer
        while buffer:
            try:
                buffer.Discard (os.write (self.fd, buffer.Pick (self.buffer_size)))
            except OSError as error:
                if error.errno == errno.EAGAIN:
                    yield self.core.Poll (self.fd, self.core.WRITE)
                else:
                    if error.errno == errno.EPIPE:
                        raise CoreDisconnectedError ()
                    raise

    #--------------------------------------------------------------------------#
    # Options                                                                  #
    #--------------------------------------------------------------------------#
    def Blocking (self, enable = None):
        return FileBlocking (self.fd, enable)

    def CloseOnExec (self, enable = None):
        return FileCloseOnExec (self.fd, enable)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Dispose (self):
        try:
            yield self.Flush ()
        finally:
            self.core.Poll (self.fd, None) # resolve with CoreDisconnectedError
            self.read_buffer.close ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
