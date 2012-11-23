# -*- coding: utf-8 -*-
import os

from .file import BufferedFile
from ..async import Async, AsyncReturn
from ..future import Future

__all__ = ('Pipe',)
#------------------------------------------------------------------------------#
# Pipe                                                                         #
#------------------------------------------------------------------------------#
class Pipe (object):
    """Asynchronous pipe wrapper
    """
    def __init__ (self, fds = None, buffer_size = None, core = None):
        if fds is None:
            read_fd, write_fd = os.pipe ()
            self.read  = BufferedFile (read_fd, buffer_size, True, core)
            self.write = BufferedFile (write_fd, buffer_size, True, core)

        else:
            self.read = None
            if fds [0] is not None:
                self.read = BufferedFile (fds [0], buffer_size, False, core)

            self.write = None
            if fds [1] is not None:
                self.write = BufferedFile (fds [1], buffer_size, False, core)

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Read (self):
        """Readable side of the pipe
        """
        return self.read

    @property
    def Write (self):
        """Writable side of the pipe
        """
        return self.write

    #--------------------------------------------------------------------------#
    # Detach                                                                   #
    #--------------------------------------------------------------------------#
    @Async
    def DetachRead (self, fd = None, blocking = None):
        """Detach read and close write descriptors
        """
        if self.read is None:
            raise ValueError ('Has already been detached')

        # options
        self.read.Blocking (blocking is None or blocking)

        # detach
        stream_fd = yield self.read.Detach ()
        self.Dispose ()

        # duplicate if needed
        if fd is None or fd == stream_fd:
            AsyncReturn (stream_fd)

        else:
            os.dup2 (stream_fd, fd)
            os.close (stream_fd)
            AsyncReturn (fd)

    @Async
    def DetachWrite (self, fd = None, blocking = None):
        """Detach write and close read descriptors
        """
        if self.write is None:
            raise ValueError ('Has already been detached')

        # options
        self.write.Blocking (blocking is None or blocking)

        # detach
        stream_fd = yield self.write.Detach ()
        self.Dispose ()

        # duplicate if needed
        if fd is None or fd == stream_fd:
            AsyncReturn (stream_fd)

        else:
            os.dup2 (stream_fd, fd)
            os.close (stream_fd)
            AsyncReturn (fd)

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    @Async
    def Dispose (self):
        """Dispose pipe
        """
        dispose = []

        read, self.read = self.read, None
        if read is not None:
            dispose.append (read.Dispose ())

        write, self.write = self.write, None
        if write is not None:
            dispose.append (write.Dispose ())

        yield Future.WhenAll (dispose)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

    #--------------------------------------------------------------------------#
    # Representation                                                           #
    #--------------------------------------------------------------------------#
    def __repr__ (self):
        """Pipe string representation
        """
        return '<Pipe [read:{} write:{}] at {}>'.format (
            self.read and self.read.Fd,
            self.write and self.write.Fd,
            id (self))

# vim: nu ft=python columns=120 :
