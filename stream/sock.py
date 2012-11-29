# -*- coding: utf-8 -*-
import socket
import errno

from .stream import StreamContext
from .file import File
from .buffered import BufferedStream
from ..async import Async, AsyncReturn
from ..core.error import BrokenPipeError, BlockingErrorSet, PipeErrorSet

__all__ = ('Socket', 'BufferedSocket',)
#------------------------------------------------------------------------------#
# Socket                                                                       #
#------------------------------------------------------------------------------#
class Socket (File):
    """Asynchronous raw socket
    """

    def __init__ (self, sock, core = None):
        self.sock = sock

        self.connecting = StreamContext ('connecting', self,
            self.FLAG_CONNECTING, self.FLAG_DISPOSING | self.FLAG_DISPOSED)
        self.accepting = StreamContext ('accepting', self,
            self.FLAG_ACCEPTING, self.FLAG_DISPOSING | self.FLAG_DISPOSED)

        File.__init__ (self, sock.fileno (), False, core)

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

                except socket.error as error:
                    if error.errno not in BlockingErrorSet:
                        if error.errno in PipeErrorSet:
                            raise BrokenPipeError (error.errno, error.strerror)
                        raise

                yield self.core.FileAwait (self.fd, self.core.READ, cancel)

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

                except socket.error as error:
                    if error.errno not in BlockingErrorSet:
                        if error.errno in PipeErrorSet:
                            raise BrokenPipeError (error.errno, error.strerror)
                        raise

                yield self.core.FileAwait (self.fd, self.core.WRITE, cancel)

    #--------------------------------------------------------------------------#
    # Connect                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Connect (self, address, cancel = None):
        """Connect asynchronously to address
        """
        with self.connecting:
            while True:
                try:
                    self.sock.connect (address)
                    AsyncReturn (self)

                except socket.error as error:
                    if error.errno not in BlockingErrorSet:
                        raise

                yield self.core.FileAwait (self.fd, self.core.WRITE, cancel)

    #--------------------------------------------------------------------------#
    # Accept                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Accept (self, cancel = None):
        """Asynchronously accept connection
        """
        with self.accepting:
            while True:
                try:
                    client, addr = self.sock.accept ()
                    AsyncReturn ((Socket (client, self.core), addr))

                except socket.error as error:
                    if error.errno not in BlockingErrorSet:
                        raise

                yield self.core.FileAwait (self.fd, self.core.READ, cancel)

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
    # Shutdown                                                                 #
    #--------------------------------------------------------------------------#
    def Shutdown (self, how):
        """Shutdown socket
        """
        self.sock.shutdown (how)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Dispose (self, cancel = None):
        """Dispose socket
        """
        if self.Disposed:
            return

        try:
            yield File.Dispose (self, cancel)
        finally:
            sock, self.sock = self.sock, None
            sock.close ()

    #--------------------------------------------------------------------------#
    # Detach                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Detach (self, cancel = None):
        """Detach socket object

        Put the stream into closed state without actually closing the underlying
        socket. The socket is returned, and can be reused for other purposes.
        """
        if self.Disposed:
            raise RuntimeError ('Socket is disposed')

        try:
            yield File.Dispose (self, cancel)
        finally:
            sock, self.sock = self.sock, None

        AsyncReturn (sock)

    #--------------------------------------------------------------------------#
    # Options                                                                  #
    #--------------------------------------------------------------------------#
    def Blocking (self, enable = None):
        """Set or get "blocking" value

        If enable is not set, returns current "blocking" value.
        """
        if enable is None:
            return self.sock.gettimeout () != 0.0

        self.sock.setblocking (enable)
        return enable

#------------------------------------------------------------------------------#
# Buffered Socket                                                              #
#------------------------------------------------------------------------------#
class BufferedSocket (BufferedStream):
    """Buffered asynchronous socket
    """
    def __init__ (self, sock, buffer_size = None, core = None):
        BufferedStream.__init__ (self, Socket (sock, core), buffer_size)

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
        """Asynchronously accept connection
        """
        sock, addr = yield self.base.Accept ()
        AsyncReturn ((BufferedSocket (sock.Socket, self.buffer_size, sock.core), addr))

# vim: nu ft=python columns=120 :
