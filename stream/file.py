# -*- coding: utf-8 -*-
import os
import errno
import fcntl

from .stream import Stream
from .buffered import BufferedStream
from ..future import RaisedFuture
from ..async import Async, AsyncReturn
from ..core import Core, POLL_READ, POLL_WRITE
from ..core.error import BrokenPipeError, BlockingErrorSet, PipeErrorSet

__all__ = ('File', 'BufferedFile', 'BlockingFD', 'CloseOnExecFD',)
#------------------------------------------------------------------------------#
# File                                                                         #
#------------------------------------------------------------------------------#
class File (Stream):
    """Asynchronous raw File
    """

    def __init__ (self, fd, closefd = None, core = None):
        Stream.__init__ (self)

        self.fd = fd
        self.closefd = closefd is None or closefd
        self.core = core or Core.Instance ()

        self.Blocking (False)

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
        """File descriptor
        """
        return self.fd

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
                    data = os.read (self.fd, size)
                    if size and not data:
                        raise BrokenPipeError (errno.EPIPE, 'Broken pipe')
                    AsyncReturn (data)

                except OSError as error:
                    if error.errno not in BlockingErrorSet:
                        if error.errno in PipeErrorSet:
                            raise BrokenPipeError (error.errno, error.strerror)
                        raise

                yield self.core.Poll (self.fd, POLL_READ, cancel)

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
                    AsyncReturn (os.write (self.fd, data))

                except OSError as error:
                    if error.errno not in BlockingErrorSet:
                        if error.errno in PipeErrorSet:
                            raise BrokenPipeError (error.errno, error.strerror)
                        raise

                yield self.core.Poll (self.fd, POLL_WRITE, cancel)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def Dispose (self, cancel = None):
        """Dispose file
        """
        if self.Disposed:
            return

        try:
            yield Stream.Dispose (self, cancel)
        finally:
            fd, self.fd = self.fd, -1
            self.core.Poll (fd, None) # resolve with BrokenPipeError
            if self.closefd:
                os.close (fd)

        AsyncReturn (fd)

    #--------------------------------------------------------------------------#
    # Detach                                                                   #
    #--------------------------------------------------------------------------#
    def Detach (self, cancel = None):
        """Detach descriptor

        Put the stream into closed state without actually closing the underlying
        file descriptor. The file descriptor is returned, and can be reused for
        other purposes.
        """
        if self.Disposed:
            return RaisedFuture (ValueError ('File is disposed'))

        self.closefd = False
        return self.Dispose (cancel)

    #--------------------------------------------------------------------------#
    # Options                                                                  #
    #--------------------------------------------------------------------------#
    def Blocking (self, enable = None):
        """Set or get "blocking" value

        If enable is not set, returns current "blocking" value.
        """
        return BlockingFD (self.fd, enable)

    def CloseOnExec (self, enable = None):
        """Set or get "close on exec" value

        If enable is not set, returns current "close on exec" value.
        """
        return CloseOnExecFD (self.fd, enable)

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        flags = self.FlagsNames
        if self.fd > 0:
            self.Blocking ()    and flags.append ('blocking')
            self.CloseOnExec () and flags.append ('close_on_exec')

        return '<{} [fd:{} flags:{}] at {}>'.format (type (self).__name__,
            self.fd, ','.join (flags), id (self))

#------------------------------------------------------------------------------#
# Buffered File                                                                #
#------------------------------------------------------------------------------#
class BufferedFile (BufferedStream):
    """Buffered asynchronous file
    """
    def __init__ (self, fd, buffer_size = None, closefd = None, core = None):
        BufferedStream.__init__ (self, File (fd, closefd, core), buffer_size)

    #--------------------------------------------------------------------------#
    # Detach                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def Detach (self, cancel = None):
        """Detach underlying descriptor
        """
        AsyncReturn ((yield (yield BufferedStream.Detach (self, cancel)).Detach (cancel)))

#------------------------------------------------------------------------------#
# File Options                                                                 #
#------------------------------------------------------------------------------#
def BlockingFD (fd, enable = None):
    """Set or get file "blocking"

    If enable is not set, returns current "blocking" value.
    """
    return not option_fd (fd, fcntl.F_GETFL, fcntl.F_SETFL, os.O_NONBLOCK,
        None if enable is None else not enable)

def CloseOnExecFD (fd, enable = None):
    """Set or get file "close on exec" option

    If enable is not set, returns current "close on exec" value.
    """
    return option_fd (fd, fcntl.F_GETFD, fcntl.F_SETFD, fcntl.FD_CLOEXEC, enable)

def option_fd (fd, get_flag, set_flag, option_flag, enable = None):
    """Set or get file option
    """
    options = fcntl.fcntl (fd, get_flag)
    if enable is None:
        return bool (options & option_flag)

    elif enable:
        options |= option_flag

    else:
        options &= ~option_flag

    fcntl.fcntl (fd, set_flag, options)
    return enable

# vim: nu ft=python columns=120 :
