# -*- coding: utf-8 -*-
import os
import sys
import struct
import atexit
import itertools
import threading
from collections import deque

from .core import Core, CoreDisconnectedError
from .file import AsyncFile
from ..async import Async
from ..future import FutureSource, RaisedFuture

__all__ = ('ThreadPool', 'ThreadPoolError',)
#------------------------------------------------------------------------------#
# Thread Pool                                                                  #
#------------------------------------------------------------------------------#
class ThreadPoolError (Exception): pass
class ThreadPoolExit (BaseException): pass
class ThreadPool (object):
    uid_struct    = struct.Struct ('Q')
    instance_lock = threading.Lock ()
    instance      = None

    def __init__ (self, size, core = None):
        if size <= 0:
            raise ValueError ('Size must be > 0')

        self.size     = size
        self.wait     = 0
        self.threads  = set ()
        self.disposed = False

        # in queue
        self.in_lock  = threading.RLock ()
        self.in_cond  = threading.Condition (self.in_lock)
        self.in_queue = deque ()

        # out queue
        self.out_uid = (self.uid_struct.pack (uid) for uid in itertools.count ())
        self.out_uid_dispose = next (self.out_uid)
        self.out_lock = threading.RLock ()
        self.out_queue = {}

        # pipe
        in_pipe, self.out_pipe = os.pipe ()
        self.in_pipe = AsyncFile (in_pipe, core = core)

        # poll worker
        self.pool_main ().Traceback ('pool_main')

        # dispose on quit
        atexit.register (self.Dispose)

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    def Size (self, size = None):
        if size is None:
            return self.size
        elif size <= 0:
            raise ValueError ('Size must be > 0')
        else:
            with self.in_lock:
                self.size = size
                if len (self.threads) > size:
                    self.thread_exit (len (self.threads) - size)
                return size

    #--------------------------------------------------------------------------#
    # Instance                                                                 #
    #--------------------------------------------------------------------------#
    @classmethod
    def Instance (cls):
        with cls.instance_lock:
            if cls.instance is None:
                cls.instance = ThreadPool (4, Core.Instance ())
            return cls.instance

    @classmethod
    def InstanceSet (cls, instance):
        with cls.instance_lock:
            instance_prev, cls.instance = cls.instance, instance
        if instance_prev is not None and instance_prev != instance:
            instance_prev.Dispose ()
        return instance

    #--------------------------------------------------------------------------#
    # Enqueue                                                                  #
    #--------------------------------------------------------------------------#
    def __call__ (self, action, *args, **keys): return self.Enqueue (action, *args, **keys)
    def Enqueue  (self, action, *args, **keys):
        if self.disposed:
            return RaisedFuture (ThreadPoolError ('Thread pool has been disposed'))

        source = FutureSource ()

        with self.in_lock:
            self.in_queue.append ((source, action, args, keys))
            if not self.wait and len (self.threads) < self.size:
                thread = threading.Thread (target = self.thread_main)
                thread.daemon = True
                thread.start ()
                self.threads.add (thread)

            else:
                self.in_cond.notify ()

        return source.Future

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    @Async
    def pool_main (self):
        try:
            while True:
                uid = yield self.in_pipe.ReadExactly (self.uid_struct.size)
                if uid == self.out_uid_dispose: return
                with self.out_lock:
                    source, result, error = self.out_queue.pop (uid)

                try:
                    if error is None:
                        source.ResultSet (result)
                    else:
                        source.ErrorSet (error)
                except Exception: pass

        except CoreDisconnectedError: pass
        finally:
            self.Dispose ()

    def thread_exit (self, count = None):
        def action_exit (): raise ThreadPoolExit ()
        with self.in_lock:
            count = count or len (self.threads)
            self.in_queue.extendleft ((None, action_exit, [], {}) for _ in range (count))
            self.in_cond.notify (count)

    def thread_main (self):
        try:
            while True:
                with self.in_lock:
                    while not self.in_queue:
                        self.wait += 1
                        self.in_cond.wait ()
                        self.wait -= 1

                    source, action, args, keys = self.in_queue.popleft ()

                result, error = None, None
                try:
                    result = action (*args, **keys)
                except Exception:
                    error = sys.exc_info ()
                except ThreadPoolExit:
                    return

                with self.out_lock:
                    out_uid = next (self.out_uid)
                    self.out_queue [out_uid] = source, result, error
                    os.write (self.out_pipe, out_uid)
        finally:
            with self.in_lock:
                self.threads.discard (threading.current_thread ())

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        with self.in_lock:
            if self.disposed:
                return
            elif threading.current_thread () in self.threads:
                # we are inside thread pool thread
                self.Enqueue (lambda: os.write (self.out_pipe, self.out_uid_dispose))
                return
            self.disposed = True

        # unregister dispose if possible
        getattr (atexit, 'unregister', lambda _: None) (self.Dispose)

        # terminate threads
        self.thread_exit ()
        for thread in tuple (self.threads):
            thread.join ()
        os.close (self.out_pipe)

        # resolve futures
        for source, action, args, keys in self.in_queue:
            source.ErrorRaise (ThreadPoolError ('Thread poll has been disposed'))
        self.in_pipe.Dispose ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
