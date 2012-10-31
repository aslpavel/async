# -*- coding: utf-8 -*-
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
    """Asynchronous File
    """
    default_buffer_size = 1 << 16

    def __init__ (self, fd, buffer_size = None, closefd = None, core = None):
        self.fd = fd
        self.closefd = closefd is None or closefd
        self.buffer_size = buffer_size or self.default_buffer_size
        self.core = core or Core.Instance ()

        # read
        self.read_buffer = Buffer ()

        # flush
        self.flusher = SucceededFuture (None)
        self.flusher_buffer = Buffer ()

        self.Blocking (False)

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Core (self):
        """Associated core object
        """
        return self.core

    @property
    def Fd (self):
        """File descriptor
        """
        return self.fd

    #--------------------------------------------------------------------------#
    # Reading                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Read (self, size, cancel = None):
        """Read asynchronously from file

        Reads at most size and at least one byte(s).
        """
        if not size:
            AsyncReturn (b'')

        buffer = self.read_buffer
        if not buffer:
            yield self.read (buffer)

        data = buffer.Peek (size)
        buffer.Discard (size)
        AsyncReturn (data)

    @Async
    def ReadExactly (self, size, cancel = None):
        """Read asynchronously from file

        Reads exactly size bytes.
        """
        if not size:
            AsyncReturn (b'')

        buffer = self.read_buffer
        while len (buffer) < size:
            yield self.read (buffer)

        data = buffer.Peek (size)
        buffer.Discard (size)
        AsyncReturn (data)

    @Async
    def read (self, buffer):
        """Read some data into buffer asynchronously
        """
        while True:
            try:
                data = os.read (self.fd, self.buffer_size)
                if not data:
                    raise CoreDisconnectedError ()
                buffer.Put (data)
                break

            except OSError as error:
                if error.errno != errno.EAGAIN:
                    if errno.errno == errno.EPIPE:
                        raise CoreDisconnectedError ()
                    raise

            yield self.core.Poll (self.fd, self.core.READ)

    #--------------------------------------------------------------------------#
    # Writing                                                                  #
    #--------------------------------------------------------------------------#
    def Write (self, data):
        """Write to file without blocking
        """
        self.flusher_buffer.Put (data)
        if self.flusher_buffer.Length () >= self.buffer_size:
            self.Flush ()

    #--------------------------------------------------------------------------#
    # Flush                                                                    #
    #--------------------------------------------------------------------------#
    def Flush (self):
        """Flush queued writes asynchronously
        """
        if self.flusher.IsCompleted () and self.flusher_buffer:
            self.flusher = self.flusher_main ()
        return self.flusher

    @Async
    def flusher_main (self):
        """Flush coroutine
        """
        buffer = self.flusher_buffer
        while buffer:
            try:
                buffer.Discard (os.write (self.fd, buffer.Peek (self.buffer_size)))
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
        """Set file "blocking" value

        If enable is not set, returns current "blocking" value.
        """
        return FileBlocking (self.fd, enable)

    def CloseOnExec (self, enable = None):
        """Set file "close on exec" value

        If enable is not set, returns current "close on exec" value.
        """
        return FileCloseOnExec (self.fd, enable)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Dispose (self):
        """Dispose file
        """
        try:
            yield self.Flush ()
        finally:
            self.core.Poll (self.fd, None) # resolve with CoreDisconnectedError
            if self.closefd:
                os.close (self.fd)
            #self.read_buffer.close ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
