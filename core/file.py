# -*- coding: utf-8 -*-
import os
import errno
import fcntl

from .core import Core
from .stream import AsyncStream
from .error import BrokenPipeError, BlockingErrorSet, PipeErrorSet
from ..async import Async, AsyncReturn

__all__ = ('AsyncFile', 'BlockingFD', 'CloseOnExecFD',)
#------------------------------------------------------------------------------#
# Asynchronous File                                                            #
#------------------------------------------------------------------------------#
class AsyncFile (AsyncStream):
    """Asynchronous File
    """

    def __init__ (self, fd, buffer_size = None, closefd = None, core = None):
        AsyncStream.__init__ (self, buffer_size)

        self.fd = fd
        self.core = core or Core.Instance ()
        self.closefd = closefd is None or closefd

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
    def ReadRaw (self, size, cancel = None):
        """Unbuffered asynchronous read
        """
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
                AsyncReturn (os.write (self.fd, data))

            except OSError as error:
                if error.errno not in BlockingErrorSet:
                    if error.errno in PipeErrorSet:
                        raise BrokenPipeError (error.errno, error.strerror)
                    raise

            yield self.core.Poll (self.fd, self.core.WRITE, cancel)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def DisposeRaw (self):
        """Dispose file
        """
        self.core.Poll (self.fd, None) # resolve with BrokenPipeError
        if self.closefd:
            os.close (self.fd)

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
