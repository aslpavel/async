# -*- coding: utf-8 -*-
import socket
import errno
try:
    import ssl
except ImportError:
    ssl = None # no SSL support

from .sock import Socket
from .stream_buff import BufferedStream
from ..async import Async, AsyncReturn
from ..core.error import BrokenPipeError, BlockingErrorSet, PipeErrorSet

__all__ = ('SocketSSL', 'BufferedSocketSSL')
#------------------------------------------------------------------------------#
# Asynchronous SSL Socket                                                      #
#------------------------------------------------------------------------------#
class SocketSSL (Socket):
    """Asynchronous SSL Socket

    If socket has already been connected it must be wrapped with
    ssl.wrap_socket, otherwise it will be wrapped when AsyncSSLSocket.Connect
    is finished.
    """

    def __init__ (self, sock, ssl_options = None, core = None):
        self.ssl_options = ssl_options or {}
        Socket.__init__ (self, sock, core)

    #--------------------------------------------------------------------------#
    # Read                                                                     #
    #--------------------------------------------------------------------------#
    @Async
    def Read (self, size, cancel = None):
        """Unbuffered asynchronous read
        """
        with self.reading:
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

                yield self.core.WhenFile (self.fd, self.core.READ, cancel)

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    @Async
    def Write (self, data, cancel = None):
        """Unbuffered asynchronous write
        """
        with self.writing:
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

                yield self.core.WhenFile (self.fd, self.core.WRITE, cancel)

    #--------------------------------------------------------------------------#
    # Connect                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Connect (self, address, cancel = None):
        """Connect asynchronously to address
        """
        yield Socket.Connect (self, address, cancel)

        with self.connecting:
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

                yield self.core.WhenFile (self.fd, event, cancel)

    #--------------------------------------------------------------------------#
    # Accept                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Accept (self, cancel = None):
        """Asynchronously accept connection

        Returns client AsyncSSLSocket and address.
        """
        with self.accepting:
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

                    AsyncReturn ((SocketSSL (client, self.buffer_size, self.ssl_options, self.core), addr))

                except socket.error as error:
                    if error.errno not in BlockingErrorSet:
                        raise

                yield self.core.WhenFile (self.fd, self.core.READ, cancel)

#------------------------------------------------------------------------------#
# Buffered SSL Socket                                                          #
#------------------------------------------------------------------------------#
class BufferedSocketSSL (BufferedStream):
    """Buffered asynchronous SSL socket
    """
    def __init__ (self, sock, buffer_size = None, ssl_options = None, core = None):
        BufferedStream.__init__ (SocketSSL (sock, ssl_options, core), buffer_size)

    #--------------------------------------------------------------------------#
    # Detach                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Detach (self, cancel = None):
        """Detach underlying socket
        """
        AsyncReturn ((yield (yield BufferedStream.Detach (self, cancel)).Detach (cancel)))

    #--------------------------------------------------------------------------#
    # Accept                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Accept (self):
        """Accept connection
        """
        sock, addr = yield self.base.Accept ()
        AsyncReturn ((BufferedSocketSSL (sock.Socket, self.buffer_size, sock.ssl_options, sock.core), addr))

# vim: nu ft=python columns=120 :
