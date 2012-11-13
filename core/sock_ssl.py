# -*- coding: utf-8 -*-
import socket
import errno
try:
    import ssl
except ImportError:
    ssl = None # no SSL support

from .sock import AsyncSocket
from .error import BrokenPipeError, BlockingErrorSet, PipeErrorSet
from ..async import Async, AsyncReturn

__all__ = ('AsyncSSLSocket',)
#------------------------------------------------------------------------------#
# Asynchronous SSL Socket                                                      #
#------------------------------------------------------------------------------#
class AsyncSSLSocket (AsyncSocket):
    """Asynchronous SSL Socket

    If socket has already been connected it must be wrapped with
    ssl.wrap_socket, otherwise it will be wrapped when AsyncSSLSocket.Connect
    is finished.
    """

    def __init__ (self, sock, buffer_size = None, ssl_options = None, core = None):
        self.ssl_options = ssl_options or {}
        AsyncSocket.__init__ (self, sock, buffer_size, core)

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Socket (self):
        """Socket object
        """
        return self.sock

    #--------------------------------------------------------------------------#
    # Read                                                                     #
    #--------------------------------------------------------------------------#
    @Async
    def ReadRaw (self, size, cancel = None):
        """Unbuffered asynchronous read
        """
        while True:
            try:
                data = self.sock.recv (size)
                if size and not data:
                    raise BrokenPipeError (errno.EPIPE, 'Broken pipe')
                AsyncReturn (data)

            except ssl.SSLError as error:
                if error.args [0] != ssl.SSL_ERROR_WANT_READ:
                    raise

            except socket.error as error:
                if error.errno not in BlockingErrorSet:
                    if error.errno in PipeErrorSet:
                        raise BrokenPipeError (error.errno, error.strerror)
                    raise

            yield self.core.Poll (self.fd, self.core.READ, cancel)

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    @Async
    def WriteRaw (self, data, cancel = None):
        """Unbuffered asynchronous write
        """
        while True:
            try:
                AsyncReturn (self.sock.send (data))

            except ssl.SSLError as error:
                if error.args [0] != ssl.SSL_ERROR_WANT_WRITE:
                    raise

            except socket.error as error:
                if error.errno not in BlockingErrorSet:
                    if error.errno in PipeErrorSet:
                        raise BrokenPipeError (error.errno, error.strerror)
                    raise

            yield self.core.Poll (self.fd, self.core.WRITE, cancel)

    #--------------------------------------------------------------------------#
    # Connect                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Connect (self, address, cancel = None):
        """Connect asynchronously to address
        """
        yield AsyncSocket.Connect (self, address, cancel)

        # wrap socket
        self.sock = ssl.wrap_socket (self.sock, do_handshake_on_connect = False, **self.ssl_options)

        # do handshake
        while True:
            event = None
            try:
                self.sock.do_handshake ()
                AsyncReturn (self)

            except ssl.SSLError as error:
                if error.args [0] == ssl.SSL_ERROR_WANT_READ:
                    event = self.core.READ
                elif error.args [0] == ssl.SSL_ERROR_WANT_WRITE:
                    event = self.core.WRITE
                else:
                    raise

            yield self.core.Poll (self.fd, event, cancel)

    #--------------------------------------------------------------------------#
    # Accept                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Accept (self, cancel = None):
        """Asynchronously accept connection

        Returns client AsyncSSLSocket and address.
        """
        while True:
            try:
                client, addr = self.sock.accept ()

                # wrap client socket
                context = getattr (self.sock, 'context', None)
                if context:
                    # use associated context (python 3.2 or higher)
                    client = context.wrap_socket (client, server_side = True)
                else:
                    client = ssl.wrap_socket (client, server_side = True, **self.ssl_options)

                AsyncReturn ((AsyncSSLSocket (client, self.buffer_size, self.ssl_options, self.core), addr))

            except socket.error as error:
                if error.errno not in BlockingErrorSet:
                    raise

            yield self.core.Poll (self.fd, self.core.READ, cancel)

# vim: nu ft=python columns=120 :
