# -*- coding: utf-8 -*-
import sys
import threading
import itertools
from time import time
from heapq import heappush, heappop

from .poller import *
from ..future import *
from ..async import *
from ..wait import *
from ..cancel import *
from ..utils.composite import *

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
    instance_lock = threading.Lock ()
    instance      = None

    def __init__ (self, poller_name = None):
        # running
        self.running = Future ()
        self.running.ResultSet (None)

        # timer
        self.timer = Timer (self)

        # files
        self.files  = {}
        self.poller = Poller.FromName (poller_name)

    #--------------------------------------------------------------------------#
    # Instance                                                                 #
    #--------------------------------------------------------------------------#
    @classmethod
    def Instance (cls, factory = None):
        with cls.instance_lock:
            if cls.instance is None:
                cls.instance = factory () if factory else Core ()
            return cls.instance

    #--------------------------------------------------------------------------#
    # Sleep                                                                    #
    #--------------------------------------------------------------------------#
    def Sleep (self, delay):
        return self.timer.Await (time () + delay)

    def SleepUntil (self, resume):
        return self.timer.Await (resume)

    #--------------------------------------------------------------------------#
    # Poll                                                                     #
    #--------------------------------------------------------------------------#
    READ       = Poller.READ
    WRITE      = Poller.WRITE
    URGENT     = Poller.URGENT
    DISCONNECT = Poller.DISCONNECT
    ERROR      = Poller.ERROR

    def Poll (self, fd, mask):
        file = self.files.get (fd)
        if file is None:
            file = File (fd, self)
            self.files [fd] = file

        return file.Await (mask)

    #--------------------------------------------------------------------------#
    # Idle                                                                     #
    #--------------------------------------------------------------------------#
    def Idle (self):
        return self.SleepUntil (0)

    #--------------------------------------------------------------------------#
    # Run                                                                      #
    #--------------------------------------------------------------------------#
    def Run (self):
        if self.running.IsCompleted ():
            self.running = Future ()
            try:
                self.wait ()
            finally:
                self.Dispose (CoreError ('Core has terminated without resolving this future'))

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def wait (self, uids = None):
        running = AnyFuture (uid () for uid in uids) if uids else self.running
        while not running.IsCompleted ():
            when = self.timer.Resolve (time ())

            if (running.IsCompleted () or
               (not when and self.poller.IsEmpty ())):
                   return

            for fd, event in self.poller.Poll (None if when is None else max (0, when - time ())):
                file = self.files.get (fd)
                if file:
                    file.Resolve (event)

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self, error = None):
        # running
        self.running.ResultSet (None)

        # timer
        self.timer.Dispose (error)

        # files
        files, self.files = self.files, {}
        for file in self.files.values ():
            file.Dispose (error)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        if et is None:
            self.Run ()
        else:
            self.Dispose (CoreError ('Core\'s context raised an error: {}'.format (eo), eo))
        return False

#------------------------------------------------------------------------------#
# Timer                                                                        #
#------------------------------------------------------------------------------#
class Timer (object):
    __slots__ = ('core', 'index', 'queue',)

    def __init__ (self, core):
        self.core  = core

        self.index = itertools.count ()
        self.queue = []

    #--------------------------------------------------------------------------#
    # Await                                                                    #
    #--------------------------------------------------------------------------#
    def Await (self, when):
        future = Future (
            Wait   (lambda: future, self.core.wait),
            Cancel (lambda: future.ErrorRaise (FutureCanceled ())))
        heappush (self.queue, (when, next (self.index), future))
        return future

    #--------------------------------------------------------------------------#
    # Resolve                                                                  #
    #--------------------------------------------------------------------------#
    def Resolve (self, time):
        # find effected
        effected = []
        while self.queue:
            when, index, future = self.queue [0]
            if future.IsCompleted ():
                heappop (self.queue) # future has been canceled
                continue

            if when > time:
                break

            heappop (self.queue)
            effected.append ((future, when))

        # resolve
        for future, when in effected:
            future.ResultSet (when)

        return self.queue [0][0] if self.queue else None

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self, error = None):
        error = error or CoreStopped ()

        queue, self.queue = self.queue, []
        for when, index, future in queue:
            future.ErrorRaise (error)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# File                                                                         #
#------------------------------------------------------------------------------#
class File (object):
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
    @Async
    def Await (self, mask):
        if not mask or self.mask & mask:
            raise CoreError ('File is already being awaited: {}'.format (mask))

        # future
        future = Future (
            Wait   (lambda: future, self.core.wait),
            Cancel (lambda: (self.dispatch (mask), future.ErrorRaise (FutureCanceled ()))))

        # register
        if self.mask:
            self.core.poller.Modify (self.fd, self.mask | mask)
        else:
            self.core.poller.Register (self.fd, mask)

        # update state
        self.mask |= mask
        self.entries.append ((mask, future))

        AsyncReturn ((yield future))

    #--------------------------------------------------------------------------#
    # Resolve                                                                  #
    #--------------------------------------------------------------------------#
    def Resolve (self, event):
        if event & Poller.ERROR:
            error = CoreDisconnectedError () if event & Poller.DISCONNECT else CoreIOError ()
            for future in self.dispatch (self.mask):
                future.ErrorRaise (error)

        else:
            for future in self.dispatch (event):
                future.ResultSet (event)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def dispatch (self, event):
        entries, effected = [], []
        if not event:
            return effected

        # find effected
        for mask, future in self.entries:
            if mask & event:
                effected.append (future)
            else:
                entries.append ((mask, future))

        # update state
        self.mask &= ~event
        self.entries = entries

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
        error = error or CoreStopped ()

        for future in self.dispatch (self.mask):
            future.ErrorRaise (error)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
