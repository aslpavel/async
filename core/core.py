# -*- coding: utf-8 -*-
import sys
import select
from heapq import heappush, heappop
from time import time

from .error import *
from .file import *
from .socket import *
from ..future import *

__all__ = ('Core',)
#------------------------------------------------------------------------------#
# Core                                                                         #
#------------------------------------------------------------------------------#
class Core (object):
    """Asynchronous application core"""
    def __init__ (self):
        self.uid = 0
        self.timer_queue = []

        self.poll_queue = {}
        self.poller = select.poll ()

    #--------------------------------------------------------------------------#
    # Poll Interface                                                           #
    #--------------------------------------------------------------------------#
    READABLE = select.POLLIN
    WRITABLE = select.POLLOUT
    URGENT   = select.POLLPRI
    ALL      = URGENT | WRITABLE | READABLE
    ALL_ERRORS = select.POLLERR | select.POLLHUP | select.POLLNVAL

    def Poll (self, fd, mask):
        """Poll descriptor fd for events with mask"""
        if mask is 0:
            return RaisedFuture ('mask is empty')

        # create future
        uid, self.uid = self.uid, self.uid + 1
        entry = (uid, Future (lambda: self.wait_uid (uid)))
        r_entry, w_entry = self.poll_queue.get (fd, (None, None))

        # queue read
        poll_mask = 0
        if mask & self.READABLE:
            if r_entry is not None:
                return RaisedFuture (CoreError ('same fd has already been queued for reading'))
            poll_mask = self.READABLE
            r_entry = entry
        elif r_entry is not None:
            poll_mask = self.READABLE

        # queue write
        if mask & self.WRITABLE:
            if w_entry is not None:
                return RaisedFuture (CoreError ('same fd has already been queued for writing'))
            poll_mask |= self.WRITABLE
            w_entry = entry
        elif w_entry is not None:
            poll_mask |= self.WRITABLE

        # update poll
        self.poll_queue [fd] = (r_entry, w_entry)
        self.poller.register (fd, poll_mask)

        return entry [1]

    #--------------------------------------------------------------------------#
    # Factories                                                                #
    #--------------------------------------------------------------------------#
    def AsyncSocketCreate (self, sock):
        """Asynchronous socket wrapper"""
        return AsyncSocket (self, sock)

    def AsyncFileCreate (self, fd, buffer_size = None, closefd = None):
        """Asynchronous file wrapper"""
        return AsyncFile (self, fd, buffer_size, closefd)

    #--------------------------------------------------------------------------#
    # Timer Interface                                                          #
    #--------------------------------------------------------------------------#
    def SleepUntil (self, time_resume):
        """Sleep until resume time is reached"""
        # create future
        uid, self.uid = self.uid, self.uid + 1
        future = Future (lambda: self.wait_uid (uid))

        # update queue
        heappush (self.timer_queue, (time_resume, uid, future))

        return future

    def Sleep (self, delay):
        """Sleep delay seconds"""
        return self.SleepUntil (time () + delay)

    def Schedule (self, delay, action):
        """Execute action in delay seconds"""
        return self.Sleep (delay).ContinueWithFunction (lambda now: action ())

    #--------------------------------------------------------------------------#
    # Run                                                                      #
    #--------------------------------------------------------------------------#
    def Run (self):
        """Run core"""
        try:
            self.wait_uid ()
        except Exception:
            error = sys.exc_info ()

            # resolve time queue
            for time_resume, uid, future in self.timer_queue:
                future.ErrorSet (error)

            # resolve poll queue
            for entries in self.poll_queue:
                for entry in entries:
                    if entry is None:
                        continue
                    entry [1].ErrorSet (error)

            raise
        
    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def wait_uid (self, await_uid = None):
        while True:
            # timer queue
            time_now, delay = time (), None
            while True:
                if not self.timer_queue:
                    delay = None
                    break
                # pick next event
                time_resume, uid, future = self.timer_queue [0]
                if time_resume > time_now:
                    delay = (time_resume - time_now) * 1000
                    break
                # pop from queue
                heappop (self.timer_queue)
                # resolve future
                future.ResultSet (time_resume)
                # complete if its awaited uid
                if uid == await_uid: return

            # select queue
            if not self.poll_queue and delay is None:
                    return
            for fd, event in self.poller.poll (delay):
                stop = False
                if event & self.ALL_ERRORS:
                    try:
                        error = CoreHUPError () if event & select.POLLHUP else \
                                CoreNVALError () if event & select.POLLNVAL else \
                                CoreIOError ()
                        raise error
                    except CoreError:
                        error = sys.exc_info ()

                    for entry in self.poll_queue.pop (fd):
                        if entry is None:
                            continue
                        uid, future = entry
                        future.ErrorSet (error)
                        if uid == await_uid:
                            stop = True

                    self.poller.unregister (fd)
                else:
                    mask, completed = 0, []

                    # readable
                    r_entry, w_entry = self.poll_queue.pop (fd)
                    if event & select.POLLIN:
                        completed.append (r_entry)
                    elif r_entry is not None:
                        mask = select.POLLIN

                    # writable
                    if event & select.POLLOUT:
                        completed.append (w_entry)
                    elif w_entry is not None:
                        mask |= select.POLLOUT

                    # update poll
                    if mask:
                        self.poller.register (fd, mask)
                    else:
                        self.poller.unregister (fd)

                    # complete separately as continuation could have changed event mask
                    for uid, future in completed:
                        future.ResultSet (event)
                        if uid == await_uid:
                            stop = True
                if stop:
                    return

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        if et is None:
            self.Run ()
        return False

# vim: nu ft=python columns=120 :