# -*- coding: utf-8 -*-
import io
import os
import errno
import fcntl

from .fd import *
from .core import *
from ..async import *

__all__ = ('AsyncFile',)
#------------------------------------------------------------------------------#
# Asynchronous File                                                            #
#------------------------------------------------------------------------------#
class AsyncFile (object):
    default_buffer_size = 1 << 16

    def __init__ (self, fd, buffer_size = None, closefd = None, core = None):
        self.fd = fd
        self.core = core or Core.Instance ()
        self.buffer_size = self.default_buffer_size if buffer_size is None else buffer_size
        self.buffer = io.open (fd, 'rb', buffering = self.buffer_size,
            closefd = True if closefd is None else closefd)
        self.writer_queue = None
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
    def Read (self, size):
        while True:
            data = self.buffer.read (size)
            if data is None:
                try:
                    yield self.core.Poll (self.fd, self.core.READABLE)
                except CoreDisconnectedError: pass
            elif data:
                AsyncReturn (data)
            else:
                raise CoreDisconnectedError ()

    def ReadExactly (self, size):
        return (self.ReadExactlyInto (size, io.BytesIO ())
            .ContinueWithFunction (lambda buffer: buffer.getvalue ()))

    @Async
    def ReadExactlyInto (self, size, stream):
        left = size
        while left:
            data = self.buffer.read (left)
            if data is None:
                try:
                    yield self.core.Poll (self.fd, self.core.READABLE)
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
    @Async
    def Write (self, data):
        try:
            data = data [os.write (self.fd, data):]
        except OSError as error:
            if error.errno != errno.EAGAIN:
                if error.errno == errno.EPIPE:
                    raise CoreDisconnectedError ()
                raise

        while len (data):
            yield self.core.Poll (self.fd, self.core.WRITABLE)
            data = data [os.write (self.fd, data):]

    def WriteNoWait (self, data):
        # enqueue if writer is active
        if self.writer_queue is not None:
            self.writer_queue.append (data)
            return

        # try to just writer
        try:
            data = data [os.write (self.fd, data):]
        except OSError as error:
            if error.errno != errno.EAGAIN:
                if error.errno == errno.EPIPE:
                    raise CoreDisconnectedError ()
                raise

        # start writer
        if data:
            self.writer (data)

    @Async
    def writer (self, data):
        self.writer_queue = [data]
        try:
            while True:
                yield self.core.Poll (self.fd, self.core.WRITABLE)

                # write queue
                data = b''.join (self.writer_queue)
                data = data [os.write (self.fd, data):]

                # update queue
                if not data: return
                del self.writer_queue [:]
                self.writer_queue.append (data)
        finally:
            self.writer_queue = None

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
        self.buffer.close ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

    def Close (self):
        self.Dispose ()

# vim: nu ft=python columns=120 :
