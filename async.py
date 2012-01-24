# -*- coding: utf-8 -*-
"""Async/Await C# like model for asynchronous programming

Author: Pavel Aslanov
Data: 12/30/2011
"""
import sys

__all__ = ('Future', 'SucceededFuture', 'FailedFuture', 'FutureError', 'FutureCanceled', 'FutureNotReady',
    'Async', 'DummyAsync', 'AsyncReturn', 'Serialize', 'Delegate')

__version__ = '0.2'

#------------------------------------------------------------------------------#
# Base Future                                                                  #
#------------------------------------------------------------------------------#
class BaseFuture (object):
    """interface Future<out T>"""

    __slots__ = tuple ()

    def Continue (self, cont):
        """Continue with function "cont" with this future as argument

        signature:
            Continue (cont:Function<Future<T>, R>) -> Future<R>
        """
        raise NotImplementedError ()

    def ContinueWithFunction (self, cont):
        """Continue with function "cont" with result as argument

        signature:
            ContinueWithFunction (cont:Function<T, R>) -> Future<R>
        """
        raise NotImplementedError ()

    def ContinueWithAsync (self, async):
        """Continue with asynchronous function "async" and pass result as argume

        signature:
            ContinueWithAsync (async:Future<T, Future<R>>) -> Future<R>
        """
        raise NotImplementedError ()

    def Unwrap (self):
        """Unwrap

        signature:
            Future<Future<TResult>>.Unwrap () -> Future<TResult>
        """
        return UnwrapFuture (self)

    def Wait (self):
        """Wait for this future to complete

        signature:
            Wait () -> None
        """
        raise NotImplementedError ()

    def Cancel (self):
        """Cancel this future

        signature:
            Cancel () -> None
        """
        raise NotImplementedError ()

    def Result (self):
        """Get result of this future

        if future is completed successfully returns result of the future
        if future is failed reraise the error
        if future is not completed reraise FutureNotReady

        signature:
            Result () -> T
        """
        raise NotImplementedError ()

    def Error (self):
        """Error or None if future is completed successfully or not completed

        signature:
            Error () -> (ExceptionType, Exception, Traceback)?
        """
        raise NotImplementedError ()

    def IsCompleted (self):
        """Check if future is completed

        signature:
            IsCompleted () -> bool
        """
        raise NotImplementedError ()

    def __bool__ (self):
        return self.IsCompleted ()

    def __nonzero__ (self):
        """Python 2 compatibility boolean cast"""
        return self.IsCompleted ()

    def __str__ (self):
        """String representation"""
        if self.IsCompleted ():
            error = self.Error ()
            if error is None:
                return '|> {} {}|'.format (self.Result (), id (self))
            else:
                return '|~ {}:{} {}|'.format (error [0].__name__, error [1], id (self))
        else:
            return '|? None {}|'.format (id (self))
    __repr__ = __str__

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Cancel ()
        return False

# Exceptions
class FutureError (Exception): pass
class FutureNotReady (FutureError): pass
class FutureCanceled (FutureError): pass

#------------------------------------------------------------------------------#
# Completed Futures                                                            #
#------------------------------------------------------------------------------#
class CompletedFuture (BaseFuture):
    __slots__ = tuple ()
    def Continue (self, cont):
        try:
            return SucceededFuture (cont (self))
        except Exception:
            return FailedFuture (sys.exc_info ())

    def Wait (self):
        pass

    def Cancel (self):
        pass

    def IsCompleted (self):
        return True

class SucceededFuture (CompletedFuture):
    __slots__ = ('result',)

    def __init__ (self, result = None):
        self.result = result

    def ContinueWithFunction (self, cont):
        try:
            return SucceededFuture (cont (self.result))
        except Exception:
            return FailedFuture (sys.exc_info ())

    def ContinueWithAsync (self, async):
        return async (self.result)

    def Result (self):
        return self.result

    def Error (self):
        return None

class FailedFuture (CompletedFuture):
    __slots__ = ('error', )

    def __init__ (self, error):
        self.error = error

    def ContinueWithFunction (self, cont):
        return self

    def ContinueWithAsync (self, async):
        return self

    def Result (self):
        reraise (*self.error)

    def Error (self):
        return self.error

#------------------------------------------------------------------------------#
# Future                                                                       #
#------------------------------------------------------------------------------#
class Future (BaseFuture):
    __slots__ = ('result', 'error', 'complete', 'completed', 'wait')

    def __init__ (self, wait = None):
        self.result, self.error = None, None
        self.complete, self.completed = None, False
        self.wait = wait

    # Future Interface
    def Continue (self, cont):
        if self.complete is not None:
            raise FutureError ('future has already been continued')

        if self.completed:
            self.complete = dummy_complete
            try:
                return SucceededFuture (cont (self))
            except Exception:
                return FailedFuture (sys.exc_info ())

        future = Future (self.Wait)

        def complete ():
            try: future.ResultSet (cont (self))
            except Exception:
                future.ErrorSet (*sys.exc_info ())
        self.complete = complete

        return future

    def ContinueWithFunction (self, cont):
        if self.complete is not None:
            raise FutureError ('future has already been continued')

        if self.completed:
            self.complete = dummy_complete
            if self.error is None:
                try:
                    return SucceededFuture (cont (self.result))
                except Exception:
                    return FailedFuture (sys.exc_info ())
            else:
                return FailedFuture (self.error)

        future = Future (self.Wait)

        def complete ():
            if self.error is None:
                try:
                    future.ResultSet (cont (self.result))
                except Exception:
                    future.ErrorSet (*sys.exc_info ())
            else:
                future.ErrorSet (*self.error)
        self.complete = complete

        return future

    def ContinueWithAsync (self, async):
        if self.complete is not None:
            raise FutureError ('future has already been continued')

        if self.completed:
            self.complete = dummy_complete
            if self.error is None:
                return async (self.result)
            else:
                return FailedFuture (self.error)

        return ContinueWithAsyncFuture (self, async)

    def Wait (self):
        if not self.completed:
            if self.wait is None:
                raise NotImplementedError ()
            self.wait ()

    def Cancel (self):
        self.ErrorRaise (FutureCanceled ())

    def Result (self):
        if not self.completed:
            raise FutureNotReady ()

        if self.error is not None:
            reraise (*self.error)
        return self.result

    def Error (self):
        return self.error
            
    def IsCompleted (self):
        return self.completed

    # control
    def ResultSet (self, result):
        if self.completed: return
        self.completed = True

        self.result = result
        if self.complete is not None:
            self.complete ()

    def ErrorSet (self, et, eo, tb):
        if self.completed: return
        self.completed = True

        self.error = (et, eo, tb)
        if self.complete is not None:
            self.complete ()

    def ErrorRaise (self, error):
        if self.completed: return

        try: raise error
        except Exception: et, eo, tb = sys.exc_info ()

        self.ErrorSet (et, eo, tb)

dummy_complete = lambda : None

#------------------------------------------------------------------------------#
# Async                                                                        #
#------------------------------------------------------------------------------#
def Async (function):
    return lambda *args, **keys: CoroutineFuture (function (*args, **keys))

class CoroutineResult (BaseException): pass
def AsyncReturn (value):
    raise CoroutineResult (value)

class CoroutineFuture (Future):
    __slots__ = Future.__slots__ + ('coroutine', )

    def __init__ (self, coroutine):
        Future.__init__ (self)

        self.coroutine = coroutine
        self.wait = None
        self.resume (SucceededFuture (None))

    def Wait (self):
        while self.wait is not None:
            self.wait.Wait ()
        if not self.IsCompleted ():
            raise RuntimeError ('you cann\'t wait inside bound generator')

    def Cancel (self):
        if not self.IsCompleted ():
            if self.wait is None:
                raise FutureCanceled () # we are inside generator
            self.wait.Cancel ()

    def resume (self, future):
        self.wait = None
        result, error = None, None
        try:
            while True:
                future = self.coroutine.send (future.Result ()) if future.Error () is None \
                    else self.coroutine.throw (*future.Error ())

                if not future.IsCompleted ():
                    self.wait = future
                    future.Continue (self.resume)
                    return
        except CoroutineResult as ret:
            result = ret.args [0]
        except StopIteration:
            result = None
        except Exception:
            error = sys.exc_info ()

        self.wait = None
        if error is not None:
            self.ErrorSet (*error)
        else:
            self.ResultSet (result)

#------------------------------------------------------------------------------#
# Dummy Async                                                                  #
#------------------------------------------------------------------------------#
def DummyAsync (function):
    def dummy_async (*args, **keys):
        try:
            return SucceededFuture (function (*args, **keys))
        except Exception:
            return FailedFuture (sys.exc_info ())
    dummy_async.__name__ = function.__name__
    return dummy_async

#------------------------------------------------------------------------------#
# Decorator Helper                                                             #
#------------------------------------------------------------------------------#
class Decorator (object):
    __slots__ = tuple ()

    def __get__ (self, instance, owner):
        if instance is None:
            return self
        return self.BoundDecorator (self, instance)

    def __call__ (self, *args, **keys):
        raise NotImplementedError ()

    class BoundDecorator (object):
        __slots__ = ('unbound', 'instance')
        def __init__ (self, unbound, instance):
            self.unbound, self.instance = unbound, instance

        def __call__ (self, *args, **keys):
            return self.unbound (self.instance, *args, **keys)

        def __getattr__ (self, attr):
            return getattr (self.unbound, attr)

#------------------------------------------------------------------------------#
# Delegate                                                                     #
#------------------------------------------------------------------------------#
class Delegate (object):
    """Delegate decorator

    Convert asynchronous method to Delegate which if called calls
    asynchronous method synchronously and has special method Async to call
    decorated function
    """
    __slots__ = ('async',)

    def __init__ (self, async):
        self.async = async

    def __get__ (self, instance, owner):
        if instance is None:
            return self.async
        return self.BoundDelegate (self, instance)

    def __call__ (self, *args, **keys):
        future = self.async (*args, **keys)
        future.Wait ()
        return future.Result ()

    def Async (self, *args, **keys):
        return self.async (*args, **keys)

    class BoundDelegate (object):
        __slots__ = ('base', 'instance')

        def __init__ (self, base, instance):
            self.base = base
            self.instance = instance

        def __call__ (self, *args, **keys):
            return self.base (self.instance, *args, **keys)

        def Async (self, *args, **keys):
            return self.base.Async (self.instance, *args, **keys)

#------------------------------------------------------------------------------#
# Serialize                                                                    #
#------------------------------------------------------------------------------#
from collections import deque

class Serialize (Decorator):
    """Serialize calls to asynchronous function"""
    def __init__ (self, async):
        self.async, self.uid = async, 0
        self.queue, self.worker, self.wait = deque (), None, None

    def __call__ (self, *args, **keys):
        if self.worker is None:
            self.wait = self.async (*args, **keys)
            if self.wait.IsCompleted ():
                result, self.wait = self.wait, None
                return result

        uid, self.uid = self.uid, self.uid + 1
        future = Future (lambda: self.wait_uid (uid))

        if self.worker is None:
            self.worker = self.worker_run (future)
        else:
            self.queue.append ((uid, future, args, keys))

        return future

    @Async
    def worker_run (self, future):
        try: future.ResultSet ((yield self.wait))
        except Exception: future.ErrorSet (*sys.exc_info ())

        try:
            while len (self.queue):
                uid, future, args, keys = self.queue.popleft ()
                try:
                    self.wait = self.async (*args, **keys)
                    future.ResultSet ((yield self.wait))
                except Exception: future.ErrorSet (*sys.exc_info ())
        finally:
            self.wait, self.worker = None, None

    def wait_uid (self, uid):
        uid += 1
        while len (self.queue):
            if self.queue [0][0] > uid:
                return
            if self.wait is None:
                return
            self.wait.Wait ()

        if self.wait is not None:
            self.wait.Wait ()

#------------------------------------------------------------------------------#
# Unwrap Future                                                                #
#------------------------------------------------------------------------------#
class UnwrapFuture (Future):
    """Unwrap future helper"""
    __slots__ = Future.__slots__ + ('future',)

    def __init__ (self, future):
        Future.__init__ (self)

        self.future = future
        future.Continue (self.outer_cont)

    def Wait (self):
        while self.future is not None:
            self.future.Wait ()

    def outer_cont (self, outer_future):
        error = outer_future.Error ()
        if error is None:
            inner_future = outer_future.Result ()
            inner_future.Continue (self.inner_cont)
            self.future = inner_future
        else:
            self.future = None
            self.ErrorSet (*error)

    def inner_cont (self, inner_future):
        self.future = None
        error = inner_future.Error ()
        if error is None:
            self.ResultSet (inner_future.Result ())
        else:
            self.ErrorSet (*error)

#------------------------------------------------------------------------------#
# Continue With Async Future                                                   #
#------------------------------------------------------------------------------#
class ContinueWithAsyncFuture (Future):
    __slots__ = Future.__slots__ + ('async',)

    def __init__ (self, future, async):
        Future.__init__ (self)

        self.async, self.wait = async, future
        future.Continue (self.future_cont)

    def Wait (self):
        while self.wait is not None:
            self.wait.Wait ()

    def future_cont (self, future):
        error = future.Error ()
        if error is None:
            self.wait = self.async (self.wait.Result ()).Continue (self.async_cont)
        else:
            self.wait = None
            self.ErrorSet (*error)

    def async_cont (self, future):
        self.wait = None
        error = future.Error ()
        if error is None:
            self.ResultSet (future.Result ())
        else:
            self.ErrorSet (*error)

#------------------------------------------------------------------------------#
# Compatibility                                                                #
#------------------------------------------------------------------------------#
if sys.version_info [0] > 2:
    import builtins
    exec_ = getattr (builtins, "exec")
    del builtins

    def reraise (tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback (tb)
        raise value
else:
    def exec_ (code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe (1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec ("""exec code in globs, locs""")

    exec_ ("""def reraise (tp, value, tb=None):
        raise tp, value, tb""")
# vim: nu ft=python columns=120 :
