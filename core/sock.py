# -*- coding: utf-8 -*-
import socket
import errno

from .file import AsyncFile
from .error import BrokenPipeError, BlockingErrorSet, PipeErrorSet
from ..async import Async, AsyncReturn

__all__ = ('AsyncSocket',)
#------------------------------------------------------------------------------#
# Asynchronous Socket                                                          #
#------------------------------------------------------------------------------#
class AsyncSocket (AsyncFile):
    """Asynchronous socket
    """

    def __init__ (self, sock, buffer_size = None, core = None):
        AsyncFile.__init__ (self, sock.fileno (), buffer_size, False, core)

        self.sock = sock

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
    def ReadRaw (self, size):
        """Unbuffered asynchronous read
        """
        while True:
            try:
                data = self.sock.recv (self.buffer_size)
                if not data:
                    raise BrokenPipeError (errno.EPIPE, 'Broken pipe')
                AsyncReturn (data)

            except socket.error as error:
                if error.errno not in BlockingErrorSet:
                    if error.errno in PipeErrorSet:
                        raise BrokenPipeError (error.errno, error.strerror)
                    raise

            yield self.core.Poll (self.fd, self.core.READ)

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    @Async
    def WriteRaw (self, data):
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

            yield self.core.Poll (self.fd, self.core.WRITE)

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
                AsyncReturn ((AsyncSocket (client, core = self.core), addr))

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
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose socket
        """
        AsyncFile.DisposeRaw (self)
        self.sock.close ()

# vim: nu ft=python columns=120 :
