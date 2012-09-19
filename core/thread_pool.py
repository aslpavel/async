# -*- coding: utf-8 -*-
import os
import sys
import errno
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
class ThreadPool (object):
    uid_struct    = struct.Struct ('Q')
    instance_lock = threading.Lock ()
    instance      = None

    def __init__ (self, size, core = None):
        if size <= 0:
            raise ValueError ('Size must be > 0')

        self.size     = size
        self.wait     = 0
        self.threads  = []
        self.disposed = False

        # in queue
        self.in_lock  = threading.Lock ()
        self.in_cond  = threading.Condition (self.in_lock)
        self.in_queue = deque ()

        # out queue
        self.out_uid = (self.uid_struct.pack (uid) for uid in itertools.count ())
        self.out_lock  = threading.Lock ()
        self.out_queue = {}

        # pipe
        in_pipe, self.out_pipe = os.pipe ()
        self.in_pipe = AsyncFile (in_pipe, core = core)

        # poll worker
        self.pool_main ().Traceback ('pool_main')

        # dispose on quit
        atexit.register (self.Dispose)

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
            cls.instance = instance
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
                self.threads.append (thread)

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
                with self.out_lock:
                    source, result, error = self.out_queue.pop (uid)

                try:
                    if error is None:
                        source.ResultSet (result)
                    else:
                        source.ErrorSet (error)
                except Exception: pass

        except CoreDisconnectedError: pass

    def thread_main (self):
        while True:
            with self.in_lock:
                while not self.in_queue:
                    self.wait += 1
                    self.in_cond.wait ()
                    self.wait -= 1
                    if self.disposed:
                        return
                source, action, args, keys = self.in_queue.popleft ()

            result, error = None, None
            try:
                result = action (*args, **keys)
            except Exception:
                error = sys.exc_info ()

            with self.out_lock:
                out_uid = next (self.out_uid)
                self.out_queue [out_uid] = source, result, error 
                try:
                    os.write (self.out_pipe, out_uid)
                except OSError as error:
                    if error.errno == errno.EBADF:
                        return
                    raise
                
    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        if self.disposed:
            return
        self.disposed = True

        # wake threads
        with self.in_lock:
            in_queue, self.in_queue = self.in_queue, deque ()
            self.in_cond.notify_all ()

        # wait threads
        for thread in self.threads:
            thread.join ()

        # resolve futures
        for source, action, args, keys in in_queue:
            source.ErrorRaise (ThreadPoolError ('Thread poll has been disposed'))
    
        # close pipe
        os.close (self.out_pipe)
        self.in_pipe.Dispose ()

    def __enter__ (self):
        return self
    
    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
