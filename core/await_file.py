import errno

from .poller import Poller
from .error import BrokenPipeError, ConnectionError
from ..future import FutureSource, FutureCanceled, RaisedFuture, SucceededFuture

__all__ = ('FileAwaiter',)
#------------------------------------------------------------------------------#
# File Await Object                                                            #
#------------------------------------------------------------------------------#
class FileAwaiter (object):
    """File await object
    """
    __slots__ = ('fd', 'poller', 'mask', 'entries',)

    def __init__ (self, fd, poller):
        self.fd = fd
        self.poller = poller

        # state
        self.mask = 0
        self.entries = []

    #--------------------------------------------------------------------------#
    # Await                                                                    #
    #--------------------------------------------------------------------------#
    def Await (self, mask, cancel = None):
        """Await event specified by mask argument
        """
        if mask is None:
            self.Dispose (BrokenPipeError (errno.EPIPE, 'Detached from core'))
            return SucceededFuture (None)
        elif not mask:
            return RaisedFuture (ValueError ('Empty event mask'))
        elif mask & self.mask:
            return RaisedFuture (ValueError ('Intersecting event mask: {}'.format (self)))

        # source
        source = FutureSource ()
        if cancel:
            cancel.Continue (lambda *_: (self.dispatch (mask), source.ErrorRaise (FutureCanceled ())))

        # register
        if self.mask:
            self.poller.Modify (self.fd, self.mask | mask)
        else:
            self.poller.Register (self.fd, mask)

        # update state
        self.mask |= mask
        self.entries.append ((mask, source))

        return source.Future

    #--------------------------------------------------------------------------#
    # Resolve                                                                  #
    #--------------------------------------------------------------------------#
    def Resolve (self, event):
        """Resolve pending events effected by specified event mask
        """
        if event & ~Poller.ERROR:
            for source in self.dispatch (event):
                source.ResultSet (event)

        else:
            error = BrokenPipeError (errno.EPIPE, 'Broken pipe') if event & Poller.DISCONNECT else \
                    ConnectionError ()
            for source in self.dispatch (self.mask):
                source.ErrorRaise (error)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def dispatch (self, event):
        """Dispatch sources effected by specified event mask
        """
        entries, effected = [], []

        # find effected
        for mask, source in self.entries:
            if mask & event:
                effected.append (source)
            else:
                entries.append ((mask, source))

        # update state
        self.mask &= ~event
        self.entries = entries

        if self.mask:
            self.poller.Modify (self.fd, self.mask)
        else:
            self.poller.Unregister (self.fd)

        return effected

    def __str__  (self):
        """String representation
        """
        events = []
        self.mask & Poller.READ  and events.append ('read')
        self.mask & Poller.WRITE and events.append ('write')
        self.mask & Poller.ERROR and events.append ('error')
        return '<FileAwaiter [fd:{} events:{}] at {}>'.format (self.fd, ','.join (events), id (self))
    __repr__ = __str__

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self, error = None):
        """Dispose file and resolve all pending events with specified error
        """
        error = error or FutureCanceled ('File await object has been disposed')

        for source in self.dispatch (self.mask):
            source.ErrorRaise (error)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
