# -*- coding: utf-8 -*-
import sys
import threading
from time import time
if sys.version_info [0] > 2:
    from _thread import get_ident
else:
    from thread import get_ident

from .poller import Poller
from .notifier import Notifier
from .await_file import FileAwaiter
from .await_time import TimeAwaiter
from .await_context import ContextAwaiter
from ..future import FutureCanceled, RaisedFuture

__all__ = ('Core',)
#------------------------------------------------------------------------------#
# Core                                                                         #
#------------------------------------------------------------------------------#
class Core (object):
    """Core object

    Asynchronous I/O and Timer dispatcher. Executes until all requested
    asynchronous operation are completed or when object itself is disposed.
    All interaction with the Core must be done from that Core's thread,
    exception are WhenContext() and Notify().
    """
    instance_lock = threading.Lock ()
    instance      = None

    FLAG_NONE     = 0x0
    FLAG_RUNNING  = 0x1
    FLAG_DISPOSED = 0x2

    def __init__ (self, poller_name = None):
        self.poller = Poller.FromName (poller_name)
        self.thread_ident = None
        self.flags = self.FLAG_NONE

        # await objects
        self.timer = TimeAwaiter ()
        self.context = ContextAwaiter (self)
        self.files = {}

        # notifier
        self.notifier = Notifier (self)

    #--------------------------------------------------------------------------#
    # Instance                                                                 #
    #--------------------------------------------------------------------------#
    @classmethod
    def Instance (cls, instance = None):
        """Global core instance

        Returns current global core instance, creates it if needed.
        """
        try:
            with cls.instance_lock:
                if instance is None:
                    if cls.instance is None:
                        cls.instance = Core ()
                else:
                    if instance is cls.instance:
                        return instance
                    instance, cls.instance = cls.instance, instance
                return cls.instance
        finally:
            if instance:
                instance.Dispose ()

    #--------------------------------------------------------------------------#
    # Time                                                                     #
    #--------------------------------------------------------------------------#
    def WhenTime (self, resume, cancel = None):
        """Resolved when specified unix time is reached

        Result of the future is scheduled time or FutureCanceled if it was
        canceled.
        """
        if self.flags & self.FLAG_DISPOSED:
            return RaisedFuture (FutureCanceled ('Core is stopped'))

        return self.timer.Await (resume, cancel)

    def WhenTimeDelay (self, delay, cancel = None):
        """Resolved after specified delay in seconds

        Result of the future is scheduled time.
        """
        if self.flags & self.FLAG_DISPOSED:
            return RaisedFuture (FutureCanceled ('Core is stopped'))

        return self.timer.Await (time () + delay, cancel)

    #--------------------------------------------------------------------------#
    # Idle                                                                     #
    #--------------------------------------------------------------------------#
    def WhenIdle (self, cancel = None):
        """Resolved when new iteration is started.

        Result of the future is None of FutureCanceled if it was canceled.
        """
        return self.WhenTime (0, cancel)

    #--------------------------------------------------------------------------#
    # Context                                                                  #
    #--------------------------------------------------------------------------#
    def WhenContext (self):
        """Resolved inside core thread

        It is safe to call this method from any thread at any time. WhenContext()
        may be used to transfer control from other threads to the Core's thread.
        """
        if self.flags & self.FLAG_DISPOSED:
            return RaisedFuture (FutureCanceled ('Core is stopped'))

        return self.context.Await ()

    #--------------------------------------------------------------------------#
    # Poll                                                                     #
    #--------------------------------------------------------------------------#
    READ       = Poller.READ
    WRITE      = Poller.WRITE
    URGENT     = Poller.URGENT
    DISCONNECT = Poller.DISCONNECT
    ERROR      = Poller.ERROR

    def WhenFile (self, fd, mask, cancel = None):
        """Poll file descriptor

        Poll file descriptor for events specified by mask. If mask is None then
        specified descriptor is unregistered and all pending events are resolved
        with BrokenPipeError, otherwise future is resolved with bitmap of
        the events happened of file descriptor or error if any.
        """
        if self.flags & self.FLAG_DISPOSED:
            return RaisedFuture (FutureCanceled ('Core is stopped'))

        assert fd >= 0, 'Invalid file descriptor: {}'.format (fd)

        file = self.files.get (fd)
        if file is None:
            file = FileAwaiter (fd, self.poller)
            self.files [fd] = file

        return file.Await (mask, cancel)

    #--------------------------------------------------------------------------#
    # Notify                                                                   #
    #--------------------------------------------------------------------------#
    def Notify (self):
        """Notify core that it must be waken
        """
        if self.flags & self.FLAG_DISPOSED:
            raise RuntimeError ('Core is disposed')

        if self.thread_ident != get_ident ():
            self.notifier ()

    #--------------------------------------------------------------------------#
    # Start|Stop                                                               #
    #--------------------------------------------------------------------------#
    def __call__ (self): return self.Execute ()
    def Execute  (self):
        """Start execution of the core
        """
        if self.flags & self.FLAG_DISPOSED:
            raise RuntimeError ('Core is disposed')

        state_running = self.FLAG_RUNNING
        if self.flags & state_running:
            return

        self.flags ^= state_running
        try:
            for _ in self.Iterator ():
                if not self.flags & state_running:
                    break
        finally:
            self.Dispose ()

    #--------------------------------------------------------------------------#
    # Iterate                                                                  #
    #--------------------------------------------------------------------------#
    def __iter__ (self): return self.Iterator ()
    def Iterator (self, block = True):
        """Core's iterator

        Returns generator object which yield at the beginning of each iteration.
        """
        if self.flags & self.FLAG_DISPOSED:
            raise RuntimeError ('Core is disposed')

        top_level = False
        try:
            # Thread identity is used by Notify to make sure call to notifier is
            # really needed. And it also used to make sure core is iterating only
            # on one thread.
            if self.thread_ident is None:
                self.thread_ident = get_ident ()
                top_level = True # top level iterator (no other iterators)
            elif self.thread_ident != get_ident ():
                raise ValueError ('Core is already being run on a different thread')

            events = tuple ()
            while True:
                # resolve await objects
                for fd, event in events:
                    self.files [fd].Resolve (event)
                self.context.Resolve ()
                self.timer.Resolve ()

                # Yield control to check conditions before blocking (Stopped
                # or desired future has been resolved). If there is no file
                # descriptors registered and timeout is negative poller will raise
                # StopIteration and break this loop.
                yield
                events = self.poller.Poll (max (self.timer.Timeout (), self.context.Timeout ()))

        finally:
            if top_level:
                self.thread_ident = None

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self, error = None):
        """Dispose core

        If there is any unresolved asynchronous operations, they are resolved
        either with ``error`` if it is set or FutureCanceled exception.
        """
        if self.flags & self.FLAG_DISPOSED:
            return
        self.flags &= ~self.FLAG_RUNNING # unset running flag
        self.flags ^= self.FLAG_DISPOSED # set disposed flag

        # resolve all futures
        error = error or FutureCanceled ('Core has been stopped')
        files, self.files = self.files, {}
        for file in files.values ():
            file.Dispose (error)
        self.context.Dispose (error)
        self.timer.Dispose (error)

        # dispose managed resources
        self.poller.Dispose ()
        self.notifier.Dispose ()

        # reset global instance if needed
        with self.instance_lock:
            if self is self.instance:
                self.instance = None

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose (eo)
        return False

    #--------------------------------------------------------------------------#
    # Representation                                                           #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation of the core
        """
        flags = []
        self.flags & self.FLAG_RUNNING  and flags.append ('running')
        self.flags & self.FLAG_DISPOSED and flags.append ('disposed')
        return '<{} [flags:{}] at {}'.format (type (self).__name__, ','.join (flags), id (self))
    __repr__ = __str__

# vim: nu ft=python columns=120 :
