# -*- coding: utf-8 -*-
import io, socket, errno

# local
from .error import *
from ..async import *

__all__ = ('AsyncSocket',)
#------------------------------------------------------------------------------#
# Asynchronous Socket                                                          #
#------------------------------------------------------------------------------#
class AsyncSocket (object):
    def __init__ (self, core, sock):
        self.core = core
        self.sock = sock
        self.fd = sock.fileno ()
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
    def Read (self, size):
        try:
            data = self.sock.recv (size)
            if not data:
                raise CoreHUPError ()
            AsyncReturn (data)
        except socket.error as error:
            if error.errno != errno.EAGAIN:
                raise

        yield self.core.Poll (self.fd, self.core.READABLE)
        AsyncReturn (self.sock.recv (size))

    def ReadExactly (self, size):
        return (self.ReadExactlyInto (size, io.BytesIO ())
            .ContinueWithFunction (lambda buffer: buffer.getvalue ()))

    @Async
    def ReadExactlyInto (self, size, stream):
        while stream.tell () < size:
            try:
                data = self.sock.recv (size - stream.tell ())
                if not data:
                    raise CoreHUPError ()
                stream.write (data)
                continue
            except socket.error as error:
                if error.errno != errno.EAGAIN:
                    if error.errno == errno.EPIPE:
                        raise CoreHUPError ()
                    raise

            yield self.core.Poll (self.fd, self.core.READABLE)
        AsyncReturn (stream)
    #--------------------------------------------------------------------------#
    # Writing                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Write (self, data):
        try:
            data = data [self.sock.send (data):]
        except socket.errno as error:
            if error.errno != errno.EAGAIN:
                if error.errno == errno.EPIPE:
                    raise CoreHUPError ()
                raise

        while len (data):
            yield self.core.Poll (self.fd, self.core.WRITABLE)
            data = data [self.sock.send (data):]

    #--------------------------------------------------------------------------#
    # Connect                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Connect (self, address):
        try:
            self.sock.connect (address)
        except socket.errno as error:
            if error.errno not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                raise
        yield self.core.Poll (self.fd, self.core.WRITABLE)

    #--------------------------------------------------------------------------#
    # Bind                                                                     #
    #--------------------------------------------------------------------------#
    def Bind (self, address):
        self.sock.bind (address)

    #--------------------------------------------------------------------------#
    # Listen                                                                   #
    #--------------------------------------------------------------------------#
    def Listen (self, backlog):
        self.sock.listend (backlog)

    #--------------------------------------------------------------------------#
    # Accept                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Accept (self):
        try:
            client, addr = self.sock.accept ()
            AsyncReturn ((self.core.AsyncSocketCreate (client), addr))
        except socket.error as error:
            if error.errno != errno.EAGAIN:
                raise

        yield self.core.Poll (self.fd, self.core.READABLE)
        client, addr = self.sock.accept ()
        AsyncReturn ((self.core.AsyncSocketCreate (client), addr))

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
