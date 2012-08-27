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
    def __init__ (self, sock, core = None):
        self.sock = sock
        self.core = core or Core.Instance ()
        self.fd = sock.fileno ()

        self.writer = SucceededFuture (None)
        self.writer_buffer = Buffer ()

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
        if self.writer.IsCompleted ():
            # fast write
            try:
                data = data [self.sock.send (data):]
            except socket.error as error:
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
                buffer.Discard (self.sock.send (buffer.Get (self.buffer_size)))
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
    def Connect (self, address):
        try:
            self.sock.connect (address)
        except socket.error as error:
            if error.errno not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                raise
        yield self.core.Poll (self.fd, self.core.WRITE)

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
    def Accept (self):
        try:
            client, addr = self.sock.accept ()
            AsyncReturn ((AsyncSocket (client, core = self.core), addr))
        except socket.error as error:
            if error.errno != errno.EAGAIN:
                raise

        yield self.core.Poll (self.fd, self.core.READ)
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
    def Dispose (self):
        self.sock.close ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

    def Close (self):
        self.Dispose ()

# vim: nu ft=python columns=120 :
