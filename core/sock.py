# -*- coding: utf-8 -*-
import io
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
    default_buffer_size = 1 << 16

    def __init__ (self, sock, buffer_size = None, core = None):
        self.sock = sock
        self.fd = sock.fileno ()
        self.core = core or Core.Instance ()
        self.buffer_size = buffer_size or self.default_buffer_size

        # flush
        self.flusher = SucceededFuture (None)
        self.flusher_buffer = Buffer ()

        sock.setblocking (False)

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Socket (self):
        return self.sock

    @property
    def Core (self):
        return self.core

    #--------------------------------------------------------------------------#
    # Reading                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Read (self, size, cancel = None):
        while True:
            try:
                data = self.sock.recv (size)
                if not data:
                    raise CoreDisconnectedError ()
                AsyncReturn (data)

            except socket.error as error:
                if error.errno != errno.EAGAIN:
                    if error.errno == errno.EPIPE:
                        raise CoreDisconnectedError ()
                    raise

            try:
                yield self.core.Poll (self.fd, self.core.READ, cancel)
            except CoreDisconnectedError: pass

    def ReadExactly (self, size, cancel = None):
        return (self.ReadExactlyInto (size, io.BytesIO (), cancel)
            .ContinueWithFunction (lambda buffer: buffer.getvalue ()))

    @Async
    def ReadExactlyInto (self, size, stream, cancel = None):
        left = size
        while left:
            try:
                data = self.sock.recv (left)
                if not data:
                    raise CoreDisconnectedError ()
                stream.write (data)
                left -= len (data)
                continue

            except socket.error as error:
                if error.errno != errno.EAGAIN:
                    if error.errno == errno.EPIPE:
                        raise CoreDisconnectedError ()
                    raise

            try:
                yield self.core.Poll (self.fd, self.core.READ, cancel)
            except CoreDisconnectedError: pass

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
                buffer.Discard (self.sock.send (buffer.Pick (self.buffer_size)))
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
        self.sock.bind (address)

    #--------------------------------------------------------------------------#
    # Listen                                                                   #
    #--------------------------------------------------------------------------#
    def Listen (self, backlog):
        self.sock.listen (backlog)

    #--------------------------------------------------------------------------#
    # Accept                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Accept (self, cancel = None):
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
            self.sock.close ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
