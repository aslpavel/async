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
        self.count = 0

        self.time_queue = []
        self.file_queue = {}

        self.poller = select.poll ()

    #--------------------------------------------------------------------------#
    # Sleep                                                                    #
    #--------------------------------------------------------------------------#
    def SleepUntil (self, resume):
        # create future
        self.count += 1
        uid, self.uid = self.uid, self.uid + 1
        def cancel ():
            if future.IsCompleted ():
                self.count -= 1
                future.ErrorRaise (FutureCacnceled ())
        future = Future (Wait (uid, self.wait), Cancel (cancel))

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
    READABLE = select.POLLIN
    WRITABLE = select.POLLOUT
    URGENT   = select.POLLPRI
    ALL      = URGENT | WRITABLE | READABLE
    ALL_ERRORS = select.POLLERR | select.POLLHUP | select.POLLNVAL

    def Poll (self, fd, mask):
        # create future
        self.count += 1
        uid, self.uid = self.uid, self.uid + 1
        def cancel ():
            if not future.IsCompleted ():
                self.count -= 1
                file.Dispatch (mask)
                future.ErrorRaise (FutureCanceled ())
        future = Future (Wait (uid, self.wait), Cancel (cancel))

        # enqueue
        file = self.file_queue.get (fd)
        if file is None:
            file = File (fd, self.poller)
            self.file_queue [fd] = file
        self.poller.register (fd, file.Enqueue (mask, uid, future))

        return future

    #--------------------------------------------------------------------------#
    # Factories                                                                #
    #--------------------------------------------------------------------------#
    def AsyncSocketCreate (self, sock):
        return AsyncSocket (self, sock)

    def AsyncFileCreate (self, fd, buffer_size = None, closefd = None):
        return AsyncFile (self, fd, buffer_size, closefd)

    #--------------------------------------------------------------------------#
    # Run                                                                      #
    #--------------------------------------------------------------------------#
    def Run (self):
        try:
            self.wait ()
        except Exception:
            error = sys.exc_info ()

            # time queue
            time_queue, self.time_queue = self.time_queue, []
            for resume, uid, future in time_queue:
                self.count -= 1
                future.ErrorSet (error)

            # file queue
            for file in list (self.file_queue.values ()):
                for uid, future in file.Dispatch (file.mask):
                    self.count -= 1
                    future.ErrorSet (error)

            raise

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def wait (self, uids = None):
        if uids and None in uids:
            return

        while True:
            # time queue
            now, delay = time (), None
            while self.time_queue:
                resume, uid, future = self.time_queue [0]
                if future.IsCompleted (): # future has been canceled
                    heappop (self.time_queue)
                    continue
                if resume > now:
                    delay = (resume - now) * 1000
                    break
                heappop (self.time_queue)
                self.count -= 1
                future.ResultSet (resume)
                if uids and uid in uids: return

            if not self.time_queue:
                delay = None

            # file queue
            if not self.count: return
            for fd, event in self.poller.poll (delay):
                file, stop = self.file_queue.get (fd), False
                if event & self.ALL_ERRORS:
                    try:
                        error = CoreHUPError () if event & select.POLLHUP else \
                                CoreNVALError () if event & select.POLLNVAL else \
                                CoreIOError ()
                        raise error
                    except CoreError:
                        error = sys.exc_info ()

                    for uid, future in file.Dispatch (file.mask):
                        self.count -= 1
                        future.ErrorSet (error)
                        if uids and uid in uids:
                            stop = True
                else:
                    for uid, future in file.Dispatch (event):
                        self.count -= 1
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
        entries, result = [], []
        for mask, uid, future in self.entries:
            if mask & event:
                result.append ((uid, future))
            else:
                entries.append ((mask, uid, future))

        self.mask &= ~event
        if self.mask:
            self.poller.register (self.fd, self.mask)
        else:
            self.poller.unregister (self.fd)
        self.entries = entries

        return result

# vim: nu ft=python columns=120 :
