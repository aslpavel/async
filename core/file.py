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

        # write
        self.writer = SucceededFuture (None)
        self.writer_buffer = Buffer ()

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
        if self.writer.IsCompleted ():
            # fast write
            if len (data) <= self.buffer_size:
                try:
                    data = data [os.write (self.fd, data):]
                except OSError as error:
                    if error.errno != errno.EAGAIN:
                        if error.errno == errno.EPIPE:
                            raise CoreDisconnectedError ()
                        raise

            # start writer
            if data:
                self.writer = self.writer_main (data)
        else:
            self.writer_buffer.Put (data)

        return self.writer

    @Async
    def writer_main (self, data):
        buffer = self.writer_buffer
        buffer.Put (data)

        yield self.core.Idle () # accumulate writes
        while buffer:
            try:
                buffer.Discard (os.write (self.fd, buffer.Get (self.buffer_size)))
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
    def Dispose (self):
        self.core.Poll (self.fd, None) # resolve with CoreDisconnectedError
        self.read_buffer.close ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

    def Close (self):
        self.Dispose ()

# vim: nu ft=python columns=120 :
