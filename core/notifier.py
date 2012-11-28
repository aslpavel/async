# -*- coding: utf-8 -*-
import os

from .error import BlockingErrorSet
from ..async import Async

__all__ = ('Notifier',)
#------------------------------------------------------------------------------#
# Notifier                                                                     #
#------------------------------------------------------------------------------#
class Notifier (object):
    """Core notifier

    Notifies core that there is some actions to be performed.
    """
    def __init__ (self, core):
        self.core = core
        self.read_fd, self.write_fd = os.pipe ()

        from ..stream.file import BlockingFD, CloseOnExecFD
        BlockingFD (self.read_fd, False)
        BlockingFD (self.write_fd, False)
        CloseOnExecFD (self.read_fd, True)
        CloseOnExecFD (self.write_fd, True)

        self.consumer ()

    #--------------------------------------------------------------------------#
    # Property                                                                 #
    #--------------------------------------------------------------------------#
    @property
    def Fd (self):
        """Notify file descriptor
        """
        return self.write_fd

    #--------------------------------------------------------------------------#
    # Notify                                                                   #
    #--------------------------------------------------------------------------#
    def __call__ (self):
        """Notify
        """
        try:
            os.write (self.write_fd, b'\x00')
        except OSError as error:
            if error.errno not in BlockingErrorSet:
                raise

    #--------------------------------------------------------------------------#
    # Consumer                                                                 #
    #--------------------------------------------------------------------------#
    @Async
    def consumer (self):
        """Consume all data from read side of the pipe
        """
        try:
            while True:
                try:
                    data = os.read (self.read_fd, 65536)
                    if not data:
                        break
                except OSError as error:
                    if error.errno not in BlockingErrorSet:
                        break
                yield self.core.FileAwait (self.read_fd, self.core.READ)
        finally:
            self.Dispose ()

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose notifier
        """
        read_fd, self.read_fd = self.read_fd, -1
        if read_fd >= 0:
            os.close (read_fd)
            self.core.FileAwait (read_fd, None)

        write_fd, self.write_fd = self.write_fd, -1
        if write_fd >= 0:
            os.close (write_fd)
            self.core.FileAwait (write_fd, None)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
