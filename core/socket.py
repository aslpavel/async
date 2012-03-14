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
            AsyncReturn (self.sock.recv (size))
        except socket.error as err:
            if err.errno != errno.EAGAIN:
                raise
        try:
            yield self.core.Poll (self.fd, self.core.READABLE)
            AsyncReturn (self.sock.recv (size))
        except CoreHUPError:
            AsyncReturn (b'')

    @Async
    def ReadExactly (self, size):
        data = io.BytesIO ()
        while data.tell () < size:
            chunk = self.sock.recv (size - data.tell ())
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
            data = data [self.sock.send (data):]
        except socket.errno as error:
            if error.errno != errno.EAGAIN:
                raise

        while len (data):
            yield self.core.Poll (self.fd, self.core.WRITABLE)
            data = data [self.sock.send (data):]

    #--------------------------------------------------------------------------#
    # Connect                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Connect (self, address):
        self.sock.connect (address)
        yield self.core.Poll (self.fd, self.core.WRITABLE)

    #--------------------------------------------------------------------------#
    # Bind                                                                     #
    #--------------------------------------------------------------------------#
    @DummyAsync
    def Bind (self, address):
        self.sock.bind (address)

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

# vim: nu ft=python columns=120 :
