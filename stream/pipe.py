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
            reader_fd, writer_fd = os.pipe ()
            self.reader  = BufferedFile (reader_fd, buffer_size, True, core)
            self.writer = BufferedFile (writer_fd, buffer_size, True, core)

        else:
            self.reader = None
            if fds [0] is not None:
                self.reader = BufferedFile (fds [0], buffer_size, False, core)

            self.writer = None
            if fds [1] is not None:
                self.writer = BufferedFile (fds [1], buffer_size, False, core)

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Reader (self):
        """Readable side of the pipe
        """
        return self.reader

    @property
    def Writer (self):
        """Writable side of the pipe
        """
        return self.writer

    #--------------------------------------------------------------------------#
    # Detach                                                                   #
    #--------------------------------------------------------------------------#
    def DetachReader (self, fd = None, blocking = None, cancel = None):
        """Detach read and close write descriptors
        """
        return self.detach (self.Reader, fd, blocking, cancel)

    def DetachWriter (self, fd = None, blocking = None, cancel = None):
        """Detach write and close read descriptors
        """
        return self.detach (self.Writer, fd, blocking, cancel)

    @Async
    def detach (self, stream, fd = None, blocking = None, cancel = None):
        """Detach stream and dispose the other
        """
        if stream is None:
            raise ValueError ('Pipe is disposed')

        stream.Blocking (blocking is None or blocking)
        stream_fd = yield stream.Detach (cancel)
        yield self.Dispose (cancel)

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
    def Dispose (self, cancel = None):
        """Dispose pipe
        """
        dispose = []

        reader, self.reader = self.reader, None
        if reader is not None:
            dispose.append (reader.Dispose (cancel))

        writer, self.writer = self.writer, None
        if writer is not None:
            dispose.append (writer.Dispose (cancel))

        yield Future.All (dispose)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """Pipe string representation
        """
        return '<Pipe [reader:{} writer:{}] at {}>'.format (self.reader, self.writer, id (self))

    def __rerp__ (self):
        """Pipe string representation
        """
        return str (self)

# vim: nu ft=python columns=120 :
