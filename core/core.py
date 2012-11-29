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
from .file_await import FileAwaiter
from .time_await import TimeAwaiter
from .context_await import ContextAwaiter
from ..future import FutureCanceled, RaisedFuture
from ..event import StateMachine, StateMachineGraph

__all__ = ('Core',)
#------------------------------------------------------------------------------#
# Core                                                                         #
#------------------------------------------------------------------------------#
class Core (object):
    """Core object

    Asynchronous I/O and Timer dispatcher. Executes until all requested
    asynchronous operation are completed or when object itself is disposed.
    All interaction with the Core must be done from that Core's thread,
    exception are ContextAwait() and Notify().
    """
    instance_lock = threading.Lock ()
    instance      = None

    STATE_INIT      = 'initial'
    STATE_EXECUTING = 'executing'
    STATE_DISPOSED  = 'disposed'

    STATE_GRAPH = StateMachineGraph.FromDict (STATE_INIT, {
        STATE_INIT: (STATE_EXECUTING, STATE_DISPOSED),
        STATE_EXECUTING: (STATE_DISPOSED,)
    })

    def __init__ (self, poller_name = None):
        self.poller = Poller.FromName (poller_name)
        self.thread_ident = None
        self.state = StateMachine (self.STATE_GRAPH)

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

        If ``instance`` is provided sets current global instance to ``instance``,
        otherwise returns current global instance, creates it if needed.
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
    def TimeAwait (self, resume, cancel = None):
        """Resolved when specified unix time is reached

        Result of the future is scheduled time or FutureCanceled if it was
        canceled.
        """
        if self.Disposed:
            return RaisedFuture (FutureCanceled ('Core is stopped'))

        return self.timer.Await (resume, cancel)

    def TimeDelayAwait (self, delay, cancel = None):
        """Resolved after specified delay in seconds

        Result of the future is scheduled time.
        """
        if self.Disposed:
            return RaisedFuture (FutureCanceled ('Core is stopped'))

        return self.timer.Await (time () + delay, cancel)

    #--------------------------------------------------------------------------#
    # Idle                                                                     #
    #--------------------------------------------------------------------------#
    def IdleAwait (self, cancel = None):
        """Resolved when new iteration is started.

        Result of the future is None of FutureCanceled if it was canceled.
        """
        return self.TimeAwait (0, cancel)

    #--------------------------------------------------------------------------#
    # Context                                                                  #
    #--------------------------------------------------------------------------#
    def ContextAwait (self, value = None):
        """Resolved inside core thread

        It is safe to call this method from any thread at any time. ContextAwait()
        may be used to transfer control from other threads to the Core's thread.
        """
        if self.Disposed:
            return RaisedFuture (FutureCanceled ('Core is stopped'))

        return self.context.Await (value)

    #--------------------------------------------------------------------------#
    # Poll                                                                     #
    #--------------------------------------------------------------------------#
    READ       = Poller.READ
    WRITE      = Poller.WRITE
    URGENT     = Poller.URGENT
    DISCONNECT = Poller.DISCONNECT
    ERROR      = Poller.ERROR

    def FileAwait (self, fd, mask, cancel = None):
        """Poll file descriptor

        Poll file descriptor for events specified by mask. If mask is None then
        specified descriptor is unregistered and all pending events are resolved
        with BrokenPipeError, otherwise future is resolved with bitmap of
        the events happened of file descriptor or error if any.
        """
        if self.Disposed:
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
        if self.Disposed:
            raise RuntimeError ('Core is disposed')

        if self.thread_ident != get_ident ():
            self.notifier ()

    #--------------------------------------------------------------------------#
    # Execute                                                                  #
    #--------------------------------------------------------------------------#
    @property
    def Executing (self):
        """Is core executing
        """
        return self.state.state == self.STATE_EXECUTING

    def Execute  (self):
        """Execute core
        """
        if self.state (self.STATE_EXECUTING):
            try:
                for _ in self.Iterator ():
                    if self.state.state != self.STATE_EXECUTING:
                        break
            finally:
                self.Dispose ()

    def __call__ (self):
        """Execute core
        """
        return self.Execute ()

    #--------------------------------------------------------------------------#
    # Iterate                                                                  #
    #--------------------------------------------------------------------------#
    def Iterator (self, block = True):
        """Core's iterator

        Returns generator object which yield at the beginning of each iteration.
        """
        if self.Disposed:
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
                events = self.poller.Poll (0) if not block else \
                    self.poller.Poll (max (self.timer.Timeout (), self.context.Timeout ()))

        finally:
            if top_level:
                self.thread_ident = None

    def __iter__ (self):
        """Core's iterator
        """
        return self.Iterator ()

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Disposed (self):
        return self.state.state == self.STATE_DISPOSED

    def Dispose (self, error = None):
        """Dispose core

        If there is any unresolved asynchronous operations, they are resolved
        either with ``error`` if it is set or FutureCanceled exception.
        """
        if not self.state (self.STATE_DISPOSED):
            return

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
                Core.instance = None

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose (eo)
        return False

    #--------------------------------------------------------------------------#
    # Representation                                                           #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<{} [state:{}] at {}'.format (type (self).__name__, self.state.State, id (self))

    def __repr__ (self):
        """String representation
        """
        return str (self)

# vim: nu ft=python columns=120 :
