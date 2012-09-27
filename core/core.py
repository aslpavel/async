# -*- coding: utf-8 -*-
import sys
import threading
import itertools
from time  import time
from heapq import heappush, heappop

from .poller  import Poller
from ..future import FutureSource, FutureCanceled, RaisedFuture

__all__ = ('Core', 'CoreError', 'CoreStopped', 'CoreIOError', 'CoreDisconnectedError',)
#------------------------------------------------------------------------------#
# Errors                                                                       #
#------------------------------------------------------------------------------#
class CoreError (Exception): pass
class CoreStopped (CoreError): pass
class CoreIOError (CoreError): pass
class CoreDisconnectedError (CoreIOError): pass

#------------------------------------------------------------------------------#
# Core                                                                         #
#------------------------------------------------------------------------------#
class Core (object):
    """Core object

    Asynchronous I/O and Timer dispatcher. Executes until all requested
    asynchronous operation are completed or when object itself is disposed.
    """
    instance_lock = threading.Lock ()
    instance      = None

    def __init__ (self, poller_name = None):
        self.timer  = Timer (self)
        self.files  = {}
        self.poller = Poller.FromName (poller_name)

        self.executing = False

    #--------------------------------------------------------------------------#
    # Instance                                                                 #
    #--------------------------------------------------------------------------#
    @classmethod
    def Instance (cls):
        """Get global core instance, create if it is None
        """
        with cls.instance_lock:
            if cls.instance is None:
                cls.instance = Core ()
            return cls.instance

    @classmethod
    def InstanceSet (cls, instance):
        """Set global core instance
        """
        with cls.instance_lock:
            instance_prev, cls.instance = cls.instance, instance
        if instance_prev is not None and instance_prev != instance:
            instance_prev.Dispose ()
        return instance

    #--------------------------------------------------------------------------#
    # Sleep                                                                    #
    #--------------------------------------------------------------------------#
    def Sleep (self, delay, cancel = None):
        """Resolved after specified delay in seconds

        Result of the future is scheduled time.
        """
        return self.timer.Await (time () + delay, cancel)

    def SleepUntil (self, resume, cancel = None):
        """Resolved when specified unix time is reached

        Result of the future is scheduled time or FutureCanceled if it was
        cancelled.
        """
        return self.timer.Await (resume, cancel)

    #--------------------------------------------------------------------------#
    # Idle                                                                     #
    #--------------------------------------------------------------------------#
    def Idle (self, cancel = None):
        """Resolved when new iteration loop is started.

        Result of the future is None of FutureCanceled if it was cancelled.
        """
        return self.SleepUntil (0, cancel)

    #--------------------------------------------------------------------------#
    # Poll                                                                     #
    #--------------------------------------------------------------------------#
    READ       = Poller.READ
    WRITE      = Poller.WRITE
    URGENT     = Poller.URGENT
    DISCONNECT = Poller.DISCONNECT
    ERROR      = Poller.ERROR

    def Poll (self, fd, mask, cancel = None):
        """Poll file descriptor

        Poll file descriptor for events specified by mask. If mask is None then
        specified descriptor is unregistred and all pending events are resolved
        with CoreDisconnectedError, otherwise future is resolved with bitmap of
        the events happened of file descriptor or error if any.
        """
        file = self.files.get (fd)
        if file is None:
            file = File (fd, self)
            self.files [fd] = file

        return file.Await (mask, cancel)

    #--------------------------------------------------------------------------#
    # Execute                                                                  #
    #--------------------------------------------------------------------------#
    @property
    def IsExecuting (self):
        """Core is executing
        """
        return self.executing

    def __call__ (self): return self.Execute ()
    def Execute  (self):
        """Execute core
        """
        if not self.executing:
            self.executing = True
            try:
                for none in self.Iterator ():
                    if not self.executing:
                        break
            finally:
                self.Dispose (CoreError ('Core has terminated without resolving this future'))

    def __iter__ (self): return self.Iterator ()
    def Iterator (self, block = True):
        """Make single iteration inside core's execution loop
        """
        while True:
            # timer
            when = self.timer.Resolve (time ())
            if not block:
                when = 0

            # interrupt to check completed futures
            yield

            # avoid blocking
            if when is None:
                if self.poller.IsEmpty ():
                    return
            else:
                when = max (0, when - time ())

            # files
            for fd, event in self.poller.Poll (when):
                file = self.files.get (fd)
                if file:
                    file.Resolve (event)

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self, error = None):
        """Dispose core

        If there is any unresolved asynchronous operations, they are resolved
        either resolved with error (optional argument) or CoreStopped exception.
        """
        self.executing = False

        # timer
        self.timer.Dispose (error)

        # files
        files, self.files = self.files, {}
        for file in self.files.values ():
            file.Dispose (error)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose (eo)
        return False

#------------------------------------------------------------------------------#
# Timer                                                                        #
#------------------------------------------------------------------------------#
class Timer (object):
    """Timer awaiter
    """
    __slots__ = ('index', 'queue',)

    def __init__ (self, core):
        self.index = itertools.count ()
        self.queue = []

    #--------------------------------------------------------------------------#
    # Await                                                                    #
    #--------------------------------------------------------------------------#
    def Await (self, when, cancel = None):
        """Await time specified by when argument
        """
        source = FutureSource ()
        if cancel:
            cancel.Continue (lambda _: source.ErrorRaise (FutureCanceled ()))

        heappush (self.queue, (when, next (self.index), source))
        return source.Future

    #--------------------------------------------------------------------------#
    # Resolve                                                                  #
    #--------------------------------------------------------------------------#
    def Resolve (self, time):
        """Resolve all pending event scheduled before time
        """
        # find effected
        effected = []
        while self.queue:
            when, index, source = self.queue [0]
            if source.Future.IsCompleted ():
                heappop (self.queue) # future has been cancelled
                continue

            if when > time:
                break

            heappop (self.queue)
            effected.append ((source, when))

        # resolve
        for source, when in effected:
            source.ResultSet (when)

        # when
        while self.queue:
            when, index, source = self.queue [0]
            if not source.Future.IsCompleted ():
                return when # future has been cancelled

            heappop (self.queue)
            continue

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self, error = None):
        """Dispose timer and resolve all pending events with specified error
        """
        error = error or CoreStopped ()

        queue, self.queue = self.queue, []
        for when, index, source in queue:
            source.ErrorRaise (error)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# File                                                                         #
#------------------------------------------------------------------------------#
class File (object):
    """File awaiter
    """
    __slots__ = ('fd', 'mask', 'entries', 'core',)

    def __init__ (self, fd, core):
        self.fd   = fd
        self.core = core

        # state
        self.mask    = 0
        self.entries = []

    #--------------------------------------------------------------------------#
    # Await                                                                    #
    #--------------------------------------------------------------------------#
    def Await (self, mask, cancel = None):
        """Await event specified by mask argument
        """
        if mask is None:
            self.Dispose (CoreDisconnectedError ())
            return
        elif mask & self.mask:
            return RaisedFuture (CoreError ('File is already being awaited: {}'.format (mask)))

        # source
        source = FutureSource ()
        if cancel:
            cancel.Continue (lambda _: (self.dispatch (mask), source.ErrorRaise (FutureCanceled ())))

        # register
        if self.mask:
            self.core.poller.Modify (self.fd, self.mask | mask)
        else:
            self.core.poller.Register (self.fd, mask)

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
        if event & Poller.ERROR:
            error = CoreDisconnectedError () if event & Poller.DISCONNECT else CoreIOError ()
            for source in self.dispatch (self.mask):
                source.ErrorRaise (error)

        else:
            for source in self.dispatch (event):
                source.ResultSet (event)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def dispatch (self, event):
        """Pop sources effected by specified event mask
        """
        entries, effected = [], []
        if not event:
            return effected

        # find effected
        for mask, source in self.entries:
            if mask & event:
                effected.append (source)
            else:
                entries.append ((mask, source))

        # update state
        self.mask &= ~event
        self.entries = entries

        if effected:
            if self.mask:
                self.core.poller.Modify (self.fd, self.mask)
            else:
                self.core.poller.Unregister (self.fd)

        return effected

    def __repr__ (self): return self.__str__ ()
    def __str__  (self):
        events = []
        if self.mask & Poller.READ:
            events.append ('read')
        if self.mask & Poller.WRITE:
            events.append ('write')
        if self.mask & Poller.ERROR:
            events.append ('error')
        return '<File fd:{} events:{}>'.format (self.fd, ','.join (events))

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self, error = None):
        """Dispose file and resolve all pending events with specified error
        """
        error = error or CoreStopped ()

        for source in self.dispatch (self.mask):
            source.ErrorRaise (error)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
