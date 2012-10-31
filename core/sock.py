# -*- coding: utf-8 -*-
import errno
import socket

from .fd      import FileCloseOnExec, FileBlocking
from .core    import Core, CoreDisconnectedError
from .buffer  import Buffer
from ..async  import Async, AsyncReturn
from ..future import SucceededFuture

__all__ = ('AsyncSocket',)
#------------------------------------------------------------------------------#
# Asynchronous Socket                                                          #
#------------------------------------------------------------------------------#
class AsyncSocket (object):
    """Asynchronous socket
    """
    default_buffer_size = 1 << 16

    def __init__ (self, sock, buffer_size = None, core = None):
        self.sock = sock
        self.fd = sock.fileno ()
        self.core = core or Core.Instance ()
        self.buffer_size = buffer_size or self.default_buffer_size

        # read
        self.read_buffer = Buffer ()

        # flush
        self.flusher = SucceededFuture (None)
        self.flusher_buffer = Buffer ()

        sock.setblocking (False)

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
        """Socket descriptor
        """
        return self.fd

    @property
    def Socket (self):
        """Socket object
        """
        return self.sock

    #--------------------------------------------------------------------------#
    # Reading                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Read (self, size, cancel = None):
        """Read asynchronously from socket

        Reads at most size bytes.
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
        """Read asynchronously from socket

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
                data = self.sock.recv (self.buffer_size)
                if not data:
                    raise CoreDisconnectedError ()
                buffer.Put (data)
                break

            except socket.error as error:
                if error.errno != errno.EAGAIN:
                    if error.errno == errno.EPIPE:
                        raise CoreDisconnectedError ()
                    raise

            yield self.core.Poll (self.fd, self.core.READ)

    #--------------------------------------------------------------------------#
    # Writing                                                                  #
    #--------------------------------------------------------------------------#
    def Write (self, data):
        """Write without blocking
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
                buffer.Discard (self.sock.send (buffer.Peek (self.buffer_size)))
            except socket.error as error:
                if error.errno == errno.EAGAIN:
                    yield self.core.Poll (self.fd, self.core.WRITE)
                else:
                    if error.errno == errno.EPIPE:
                        raise CoreDisconnectedError ()
                    raise

    #--------------------------------------------------------------------------#
    # Connect                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Connect (self, address, cancel = None):
        """Connect asynchronously to the socket
        """
        try:
            self.sock.connect (address)
        except socket.error as error:
            if error.errno not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                raise
        yield self.core.Poll (self.fd, self.core.WRITE, cancel)
        AsyncReturn (self)

    #--------------------------------------------------------------------------#
    # Bind                                                                     #
    #--------------------------------------------------------------------------#
    def Bind (self, address):
        """Bind socket to address
        """
        self.sock.bind (address)

    #--------------------------------------------------------------------------#
    # Listen                                                                   #
    #--------------------------------------------------------------------------#
    def Listen (self, backlog):
        """Listen socket
        """
        self.sock.listen (backlog)

    #--------------------------------------------------------------------------#
    # Accept                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Accept (self, cancel = None):
        """Asynchronously accept connection to the socket
        """
        try:
            client, addr = self.sock.accept ()
            AsyncReturn ((AsyncSocket (client, core = self.core), addr))
        except socket.error as error:
            if error.errno != errno.EAGAIN:
                raise

        yield self.core.Poll (self.fd, self.core.READ, cancel)
        client, addr = self.sock.accept ()
        AsyncReturn ((AsyncSocket (client, core = self.core), addr))

    #--------------------------------------------------------------------------#
    # Options                                                                  #
    #--------------------------------------------------------------------------#
    def Blocking (self, enable = None):
        """Set blocking "blocking" value

        If enable is not set, returns current blocking value.
        """
        return FileBlocking (self.fd, enable)

    def CloseOnExec (self, enable = None):
        """Set socket "close on exec" value

        If enable is not set, returns current "close on exec" value.
        """
        return FileCloseOnExec (self.fd, enable)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Dispose (self):
        """Dispose socket
        """
        try:
            yield self.Flush ()
        finally:
            self.core.Poll (self.fd, None) # resolve with CoreDisconnectedError
            self.sock.close ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
