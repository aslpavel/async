# -*- coding: utf-8 -*-
import threading
from time import time

from .poller import Poller
from .notifier import Notifier
from .await_file import FileAwaiter
from .await_time import TimeAwaiter
from .await_context import ContextAwaiter
from ..future import FutureCanceled

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

    def __init__ (self, poller_name = None):
        self.poller = Poller.FromName (poller_name)
        self.executing = False
        self.thread_ident = None

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
    def Instance (cls):
        """Get global core instance, creates it if it's None
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
    # Time                                                                     #
    #--------------------------------------------------------------------------#
    def WhenTime (self, resume, cancel = None):
        """Resolved when specified unix time is reached

        Result of the future is scheduled time or FutureCanceled if it was
        canceled.
        """
        return self.timer.Await (resume, cancel)

    def WhenTimeDelay (self, delay, cancel = None):
        """Resolved after specified delay in seconds

        Result of the future is scheduled time.
        """
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
        if self.thread_ident != threading.get_ident ():
            self.notifier ()

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
                self.Dispose ()

    def __iter__ (self): return self.Iterator ()
    def Iterator (self, block = True):
        """Make single iteration inside core's execution loop
        """
        topmost = False
        try:
            # Thread identity is used by Notify to make sure call to notifier is
            # really needed. And it also used to make sure core is iterating only
            # on one thread.
            if self.thread_ident is None:
                topmost = True
                self.thread_ident = threading.get_ident ()
            elif self.thread_ident != threading.get_ident ():
                raise ValueError ('Core is already being run on a different thread')

            events = tuple ()
            while True:
                # resolve await objects
                for fd, event in events:
                    self.files [fd].Resolve (event)
                self.context.Resolve ()
                self.timer.Resolve ()

                # Yield control to check conditions before blocking (Execution
                # or desired future has been resolved). If there is no file
                # descriptors registered and timeout is negative poller will raise
                # StopIteration and break this loop.
                yield
                events = self.poller.Poll (max (self.timer.Timeout (), self.context.Timeout ()))

        finally:
            if topmost:
                self.thread_ident = None

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self, error = None):
        """Dispose core

        If there is any unresolved asynchronous operations, they are resolved
        either resolved with error (optional argument) or FutureCanceled exception.
        """
        self.executing = False
        error = error or FutureCanceled ('Core has been stopped')

        # dispose notifier
        self.notifier.Dispose ()

        # dispose await objects
        files, self.files = self.files, {}
        for file in files.values ():
            file.Dispose (error)
        self.context.Dispose (error)
        self.timer.Dispose (error)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose (eo)
        return False

# vim: nu ft=python columns=120 :
