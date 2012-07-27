# -*- coding: utf-8 -*-
import sys
import select
from heapq import heappush, heappop
from time import time

from .error import *
from .file import *
from .sock import *

from ..future import *
from ..wait import *
from ..cancel import *

__all__ = ('Core',)
#------------------------------------------------------------------------------#
# Core                                                                         #
#------------------------------------------------------------------------------#
class Core (object):
    def __init__ (self):
        self.uid = 0
        self.uids = set ()
        self.running = False

        self.time_queue = []
        self.file_queue = {}

        self.poller = select.poll ()

    #--------------------------------------------------------------------------#
    # Sleep                                                                    #
    #--------------------------------------------------------------------------#
    def SleepUntil (self, resume):
        # create future
        uid, self.uid = self.uid, self.uid + 1
        def cancel ():
            self.uids.discard (uid)
            future.ErrorRaise (FutureCanceled ())
        future = Future (Wait (uid, self.wait), Cancel (cancel))
        self.uids.add (uid)

        # enqueue
        heappush (self.time_queue, (resume, uid, future))

        return future

    def Sleep (self, delay):
        return self.SleepUntil (time () + delay)

    def Schedule (self, delay, action):
        return self.Sleep (delay).ContinueWithFunction (lambda now: action ())

    #--------------------------------------------------------------------------#
    # Poll                                                                     #
    #--------------------------------------------------------------------------#
    READABLE     = select.POLLIN
    WRITABLE     = select.POLLOUT
    URGENT       = select.POLLPRI
    DISCONNECTED = select.POLLHUP
    INVALID      = select.POLLNVAL
    ERROR        = select.POLLERR
    ALL          = URGENT | WRITABLE | READABLE
    ALL_ERRORS   = ERROR | DISCONNECTED | INVALID

    def Poll (self, fd, mask):
        # create future
        uid, self.uid = self.uid, self.uid + 1
        def cancel ():
            self.uids.discard (uid)
            file.Dispatch (mask)
            future.ErrorRaise (FutureCanceled ())
        future = Future (Wait (uid, self.wait), Cancel (cancel))
        self.uids.add (uid)

        # enqueue
        file = self.file_queue.get (fd)
        if file is None:
            file = File (fd, self.poller)
            self.file_queue [fd] = file
        self.poller.register (fd, file.Enqueue (mask, uid, future))

        return future

    #--------------------------------------------------------------------------#
    # Idle                                                                     #
    #--------------------------------------------------------------------------#
    def Idle (self):
        return self.SleepUntil (0)

    #--------------------------------------------------------------------------#
    # Factories                                                                #
    #--------------------------------------------------------------------------#
    def AsyncSocketCreate (self, sock):
        return AsyncSocket (self, sock)

    def AsyncFileCreate (self, fd, buffer_size = None, closefd = None):
        return AsyncFile (self, fd, buffer_size, closefd)

    #--------------------------------------------------------------------------#
    # Run | Stop                                                               #
    #--------------------------------------------------------------------------#
    def Run (self):
        if not self.running:
            self.running = True
            try:
                self.wait ()
            finally:
                self.Stop (CoreError ('Core has terminated without resolving this future'))

    def Stop (self, error = None):
        self.running = False
        error = CoreStopped if error is None else error

        # resovle time queue
        time_queue, self.time_queue = self.time_queue, []
        for resume, uid, future in time_queue:
            future.ErrorRaise (error)

        # resovle file queue
        for file in list (self.file_queue.values ()):
            for uid, future in file.Dispatch (file.mask):
                future.ErrorRaise (error)

        # clear queues
        self.uids.clear ()
        self.file_queue.clear ()

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def wait (self, uids = None):
        if uids:
            for uid in uids:
                if uid not in self.uids:
                    return

        resume = None # initalize local variable
        while self.running or uids:
            #------------------------------------------------------------------#
            # Timer Queue                                                      #
            #------------------------------------------------------------------#
            while self.time_queue:
                resume, uid, future = self.time_queue [0]

                if future.IsCompleted ():
                    heappop (self.time_queue) # future has been canceled
                    continue

                if resume > time ():
                    break

                # resolve timer
                heappop (self.time_queue)
                self.uids.discard (uid)
                future.ResultSet (resume)
                resume = None

                if uids and uid in uids:
                    return

            #------------------------------------------------------------------#
            # File Queue                                                       #
            #------------------------------------------------------------------#
            if not self.uids: return
            for fd, event in self.poller.poll ((resume - time ()) * 1000 if resume else None):
                file, stop = self.file_queue.get (fd), False

                if event & self.ALL_ERRORS:
                    try:
                        error = CoreDisconnectedError () if event & self.DISCONNECTED else \
                                CoreInvalidError () if event & self.INVALID else \
                                CoreIOError ()
                        raise error
                    except CoreError:
                        error = sys.exc_info ()

                    for uid, future in file.Dispatch (file.mask):
                        self.uids.discard (uid)
                        future.ErrorSet (error)
                        if uids and uid in uids:
                            stop = True
                else:
                    for uid, future in file.Dispatch (event):
                        self.uids.discard (uid)
                        future.ResultSet (event)
                        if uids and uid in uids:
                            stop = True

                if stop:
                    return

    #--------------------------------------------------------------------------#
    # Context                                                                  #
    #--------------------------------------------------------------------------#
    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        if et is None:
            self.Run ()
        else:
            self.Stop (CoreError ('Core\'s context raised an error: {}'.format (eo), eo))
        return False

#------------------------------------------------------------------------------#
# File                                                                         #
#------------------------------------------------------------------------------#
class File (object):
    __slots__ = ('fd', 'mask', 'entries', 'poller')

    def __init__ (self, fd, poller):
        self.fd = fd
        self.mask = 0
        self.entries = []
        self.poller  = poller

    #--------------------------------------------------------------------------#
    # Enqueue                                                                  #
    #--------------------------------------------------------------------------#
    def Enqueue (self, mask, uid, future):
        if self.mask & mask:
            raise CoreError ('file has already been queued for this event')

        self.mask |= mask
        self.entries.append ((mask, uid, future))

        return self.mask

    #--------------------------------------------------------------------------#
    # Dispatch                                                                 #
    #--------------------------------------------------------------------------#
    def Dispatch (self, event):
        entries, effected = [], []
        if not event:
            return effected

        # find effected
        for mask, uid, future in self.entries:
            if mask & event:
                effected.append ((uid, future))
            else:
                entries.append ((mask, uid, future))

        # update mask
        self.mask &= ~event
        if self.mask:
            self.poller.register (self.fd, self.mask)
        else:
            self.poller.unregister (self.fd)
        self.entries = entries

        return effected

# vim: nu ft=python columns=120 :
