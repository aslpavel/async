# -*- coding: utf-8 -*-
import errno

from .poll import POLL_READ, POLL_WRITE, POLL_ERROR, POLL_DISCONNECT
from .error import BrokenPipeError, ConnectionError
from ..future import FutureSourcePair, FutureCanceled, RaisedFuture, CompletedFuture

__all__ = ('PollAwaiter',)
#------------------------------------------------------------------------------#
# Poll Awaiter                                                                 #
#------------------------------------------------------------------------------#
class PollAwaiter (object):
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
            return CompletedFuture (None)
        elif not mask:
            return RaisedFuture (ValueError ('Empty event mask'))
        elif mask & self.mask:
            return RaisedFuture (ValueError ('Intersecting event mask: {}'.format (self)))

        # source
        future, source = FutureSourcePair ()
        if cancel:
            def cancel_cont (result, error):
                self.dispatch (mask)
                source.TrySetCanceled ()
            cancel.Await ().OnCompleted (cancel_cont)

        # register
        if self.mask:
            self.poller.Modify (self.fd, self.mask | mask)
        else:
            self.poller.Register (self.fd, mask)

        # update state
        self.mask |= mask
        self.entries.append ((mask, source))

        return future

    #--------------------------------------------------------------------------#
    # Resolve                                                                  #
    #--------------------------------------------------------------------------#
    def Resolve (self, event):
        """Resolve pending events effected by specified event mask
        """
        if event & ~POLL_ERROR:
            for source in self.dispatch (event):
                source.TrySetResult (event)

        else:
            error = BrokenPipeError (errno.EPIPE, 'Broken pipe') if event & POLL_DISCONNECT else \
                    ConnectionError ()
            for source in self.dispatch (self.mask):
                source.TrySetException (error)

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
        self.mask & POLL_READ  and events.append ('read')
        self.mask & POLL_WRITE and events.append ('write')
        self.mask & POLL_ERROR and events.append ('error')
        return '<PollAwaiter [fd:{} events:{}] at {}>'.format (self.fd, ','.join (events), id (self))
    __repr__ = __str__

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self, error = None):
        """Dispose file and resolve all pending events with specified error
        """
        error = error or FutureCanceled ('File await object has been disposed')

        for source in self.dispatch (self.mask):
            source.TrySetException (error)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
