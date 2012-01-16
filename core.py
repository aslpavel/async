# -*- coding: utf-8 -*-
import socket, select, errno
from collections import defaultdict
from heapq import heappush, heappop
from time import time

# local
from .async import *

__all__ = ('Core', 'CoreError', 'CoreIOError', 'CoreHUPError', 'CoreNVALError')

#------------------------------------------------------------------------------#
# Errors                                                                       #
#------------------------------------------------------------------------------#
class CoreError (Exception): pass
class CoreIOError (CoreError): pass
class CoreHUPError (CoreIOError): pass
class CoreNVALError (CoreIOError): pass

#------------------------------------------------------------------------------#
# Core                                                                         #
#------------------------------------------------------------------------------#
class Core (object):
    """Asynchronous application core"""
    def __init__ (self):
        self.uid = 0
        self.timer_queue = []

        self.poller_queue = defaultdict (lambda: [0, []])
        self.poller = select.poll ()

    READABLE = select.POLLIN
    WRITABLE = select.POLLOUT
    URGENT   = select.POLLPRI
    ALL      = URGENT | WRITABLE | READABLE
    ALL_ERRORS = select.POLLERR | select.POLLHUP | select.POLLNVAL

    def Poll (self, fd, mask):
        """Poll descriptor fd for events with mask"""
        # create future
        uid, self.uid = self.uid, self.uid + 1
        future = Future (lambda: self.wait_uid (uid))

        # update queue
        entry = self.poller_queue [fd]
        if entry [0] & mask:
            raise CoreError ('Intersecting mask for the same descriptor')
        entry [0] |= mask
        entry [1].append ((mask, uid, future))
        self.poller.register (fd, entry [0])

        return future

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

    def Run (self):
        """Run core"""
        self.wait_uid ()
        
    def wait_uid (self, uid = None):
        while (len (self.timer_queue) != 0 or
               len (self.poller_queue) != 0):

            # timer queue
            time_now, delay = time (), None
            while len (self.timer_queue):
                t, u, f = self.timer_queue [0]
                if t > time_now:
                    delay = (t - time_now) * 1000
                    break
                heappop (self.timer_queue)
                if not f.completed:
                    f.ResultSet (t)
                    if u == uid: return
            if not len (self.timer_queue):
                if not len (self.poller_queue):
                    break
                delay = None

            # select queue
            for fd, event in self.poller.poll (delay):
                stop = False

                mask, waiters = self.poller_queue.pop (fd)
                self.poller.unregister (fd)
                if event & self.ALL_ERRORS:
                    if event & select.POLLHUP:
                        error = CoreHUPError ()
                    elif event & select.POLLNVAL:
                        error = CoreNVALError ()
                    else:
                        error = CoreIOError ()

                    for m, u, f in waiters:
                        f.ErrorRaise (error)
                        if u == uid: stop = True
                else:
                    mask_new, waiters_new, completed = 0, [], []
                    for m, u, f in waiters:
                        if m & event:
                            completed.append (f)
                            if u == uid: stop = True
                        else:
                            mask_new |= m
                            waiters_new.append ((m, u, f))

                    if mask_new:
                        self.poller_queue [fd] = [mask_new, waiters_new]
                        self.poller.register (fd, mask_new)

                    # complete separately as continuation could have changed event mask
                    for f in completed:
                        f.ResultSet (event)

                if stop:
                    return

    # context manager
    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        if et is None:
            self.Run ()
        return False

    def AsyncSocketCreate (self, sock):
        """Asynchronous socket wrapper"""
        return self.AsyncSocket (self, sock)

    class AsyncSocket (object):
        def __init__ (self, core, sock):
            self.core = core
            self.sock = sock
            self.fd = sock.fileno ()
            sock.setblocking (False)

        @Async
        def Recv (self, count):
            try:
                AsyncReturn (self.sock.recv (count))
            except socket.error as err:
                if err.errno != errno.EAGAIN:
                    raise
            try:
                yield self.core.Poll (self.fd, self.core.READABLE)
                AsyncReturn (self.sock.recv (count))
            except CoreHUPError:
                AsyncReturn (b'')

        @Async
        def Send (self, data):
            try:
                AsyncReturn (self.sock.send (data))
            except socket.error as err:
                if err.errno != errno.EAGAIN:
                    raise
            yield self.core.Poll (self.fd, self.core.WRITABLE)
            AsyncReturn (self.sock.send (data))

        @Async
        def Accept (self):
            try:
                client, addr = self.sock.accept ()
                AsyncReturn ((self.core.AsyncSocketCreate (client), addr))
            except socket.error as err:
                if err.errno != errno.EAGAIN:
                    raise
            yield self.core.Poll (self.fd, self.core.READABLE)
            client, addr = self.sock.accept ()
            AsyncReturn ((self.core.AsyncSocketCreate (client), addr))

        def __getattr__ (self, attr):
            return getattr (self.sock, attr)

# vim: nu ft=python columns=120 :
