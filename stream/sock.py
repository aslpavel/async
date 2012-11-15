# -*- coding: utf-8 -*-
import socket
import errno

from .file import File
from .stream_buff import BufferedStream
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

            yield self.core.Poll (self.fd, self.core.READ, cancel)

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    @Async
    def Write (self, data, cancel = None):
        """Unbuffered asynchronous write
        """
        while True:
            try:
                AsyncReturn (self.sock.send (data))

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
        while True:
            try:
                self.sock.connect (address)
                AsyncReturn (self)

            except socket.error as error:
                if error.errno not in BlockingErrorSet:
                    raise

            yield self.core.Poll (self.fd, self.core.WRITE, cancel)

    #--------------------------------------------------------------------------#
    # Accept                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Accept (self, cancel = None):
        """Asynchronously accept connection
        """
        while True:
            try:
                client, addr = self.sock.accept ()
                AsyncReturn ((Socket (client, self.core), addr))

            except socket.error as error:
                if error.errno not in BlockingErrorSet:
                    raise

            yield self.core.Poll (self.fd, self.core.READ, cancel)

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
    def Dispose (self):
        """Dispose socket
        """
        if self.disposed:
            return

        try:
            yield File.Dispose (self)
        finally:
            sock, self.sock = self.sock, None
            sock.close ()

    #--------------------------------------------------------------------------#
    # Detach                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Detach (self):
        """Detach socket object

        Put the stream into closed state without actually closing the underlying
        socket. The socket is returned, and can be reused for other purposes.
        """
        if self.disposed:
            raise ValueError ('Socket has been disposed')

        try:
            yield File.Dispose (self)
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
    # Accept                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Accept (self):
        """Asynchronously accept connection
        """
        sock, addr = yield self.base.Accept ()
        AsyncReturn ((BufferedSocket (sock.Socket, self.buffer_size, sock.core), addr))

# vim: nu ft=python columns=120 :
