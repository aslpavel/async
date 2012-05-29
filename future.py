# -*- coding: utf-8 -*-
import sys
from .compat import *
from .wait import *
from .cancel import *

__all__ = ('BaseFuture', 'Future', 'SucceededFuture', 'FailedFuture', 'RaisedFuture', 'MutableFuture',
    'FutureError', 'FutureCanceled', 'FutureNotReady',)
#------------------------------------------------------------------------------#
# Base Future                                                                  #
#------------------------------------------------------------------------------#
class BaseFuture (object):
    """Future<out T> Interface"""

    __slots__ = tuple ()

    #--------------------------------------------------------------------------#
    # Continuation                                                             #
    #--------------------------------------------------------------------------#
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
        """Continue with asynchronous function "async" and pass result as argument

        signature:
            ContinueWithAsync (async:Future<T, Future<R>>) -> Future<R>
        """
        raise NotImplementedError ()


    #--------------------------------------------------------------------------#
    # Wait                                                                     #
    #--------------------------------------------------------------------------#
    @property
    def Wait (self):
        """Wait for this future to complete

        signature:
            Wait () -> WaitObject
        """
        return RaiseWait (NotImplementedError ('Future is not waitable'))

    #--------------------------------------------------------------------------#
    # Cancel                                                                   #
    #--------------------------------------------------------------------------#
    @property
    def Cancel (self):
        """Cancel this future

        signature:
            Cancel () -> CancelObject
        """
        return RaiseCancel (NotImplementedError ('Future is not cancelable'))

    #--------------------------------------------------------------------------#
    # Result                                                                   #
    #--------------------------------------------------------------------------#
    def Result (self):
        """Get result of this future

        if future is completed successfully returns result of the future
        if future is failed raise the error
        if future is not completed raise FutureNotReady

        signature:
            Result () -> T
        """
        raise NotImplementedError ()

    #--------------------------------------------------------------------------#
    # Error                                                                    #
    #--------------------------------------------------------------------------#
    def Error (self):
        """Error or None if future is completed successfully or not completed

        signature:
            Error () -> (ExceptionType, Exception, Traceback)?
        """
        raise NotImplementedError ()

    #--------------------------------------------------------------------------#
    # Completed                                                                #
    #--------------------------------------------------------------------------#
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

    #--------------------------------------------------------------------------#
    # Resolve                                                                  #
    #--------------------------------------------------------------------------#
    def __invert__ (self):
        """Resolve future synchronously"""
        self.Wait ()
        return self.Result ()

    #--------------------------------------------------------------------------#
    # Mutate                                                                   #
    #--------------------------------------------------------------------------#
    def Unwrap (self):
        """Unwrap

        signature:
            Future<Future<TResult>>.Unwrap () -> Future<TResult>
        """
        return UnwrapFuture (self)

    #--------------------------------------------------------------------------#
    # Representation                                                           #
    #--------------------------------------------------------------------------#
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

    #--------------------------------------------------------------------------#
    # Traceback                                                                #
    #--------------------------------------------------------------------------#
    def Traceback (self, name = None):
        def traceback_cont (future):
            try: return future.Result ()
            except Exception:
                import io, traceback

                error_stream = io.StringIO () if sys.version_info [0] > 2 else io.BytesIO ()
                error_stream.write ('Future \'{}\' has terminated with error\n'.format (
                    'UNNAMED' if name is None else name))
                traceback.print_exc (file = error_stream)

                sys.stderr.write (error_stream.getvalue ())
                sys.stderr.flush ()
                raise

        return self.Continue (traceback_cont)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.Cancel ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Errors                                                                       #
#------------------------------------------------------------------------------#
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

    @property
    def Wait (self):
        return DummyWait ()

    @property
    def Cancel (self):
        return Cancel ()

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
        Raise (*self.error)

    def Error (self):
        return self.error

class RaisedFuture (FailedFuture):
    __slots__ = FailedFuture.__slots__

    def __init__ (self, error):
        try: raise error
        except Exception:
            exc_info = sys.exc_info ()
        FailedFuture.__init__ (self, exc_info)

#------------------------------------------------------------------------------#
# Future                                                                       #
#------------------------------------------------------------------------------#
class Future (BaseFuture):
    __slots__ = ('result', 'error', 'complete', 'completed', 'wait', 'cancel')

    def __init__ (self, wait = None, cancel = None):
        # results
        self.result, self.error = None, None
        # state
        self.complete, self.completed = None, False
        # wait and cancel
        self.wait = wait
        self.cancel = cancel

    #--------------------------------------------------------------------------#
    # Continuation                                                             #
    #--------------------------------------------------------------------------#
    def Continue (self, cont):
        if self.complete is not None:
            raise FutureError ('future has already been continued')

        if self.completed:
            self.complete = dummy_complete
            try:
                return SucceededFuture (cont (self))
            except Exception:
                return FailedFuture (sys.exc_info ())

        future = Future (self.Wait, self.Cancel)

        def complete ():
            try: future.ResultSet (cont (self))
            except Exception:
                future.ErrorSet (sys.exc_info ())
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

        future = Future (self.Wait, self.Cancel)

        def complete ():
            if self.error is None:
                try:
                    future.ResultSet (cont (self.result))
                except Exception:
                    future.ErrorSet (sys.exc_info ())
            else:
                future.ErrorSet (self.error)
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

    #--------------------------------------------------------------------------#
    # Wait                                                                     #
    #--------------------------------------------------------------------------#
    @property
    def Wait (self):
        if self.wait is None:
            return RaiseWait (NotImplementedError ())
        return self.wait

    #--------------------------------------------------------------------------#
    # Cancel                                                                   #
    #--------------------------------------------------------------------------#
    @property
    def Cancel (self):
        if self.cancel is None:
            return RaiseCancel (NotImplementedError ())
        return self.cancel

    #--------------------------------------------------------------------------#
    # Result                                                                   #
    #--------------------------------------------------------------------------#
    def Result (self):
        if not self.completed:
            raise FutureNotReady ()

        if self.error is not None:
            Raise (*self.error)
        return self.result

    #--------------------------------------------------------------------------#
    # Error                                                                    #
    #--------------------------------------------------------------------------#
    def Error (self):
        return self.error

    #--------------------------------------------------------------------------#
    # Completed                                                                #
    #--------------------------------------------------------------------------#
    def IsCompleted (self):
        return self.completed

    #--------------------------------------------------------------------------#
    # Resolve                                                                  #
    #--------------------------------------------------------------------------#
    def ResultSet (self, result):
        if self.completed: return
        self.completed = True

        self.result = result
        if self.complete is not None:
            self.complete ()

    def ErrorSet (self, error):
        if self.completed: return
        self.completed = True

        self.error = error
        if self.complete is not None:
            self.complete ()

    def ErrorRaise (self, exception):
        if self.completed: return

        try: raise exception
        except Exception:
            error = sys.exc_info ()

        self.ErrorSet (error)

dummy_complete = lambda : None

#------------------------------------------------------------------------------#
# Mutable Future                                                               #
#------------------------------------------------------------------------------#
class MutableFuture (Future):
    __slots__ = Future.__slots__

    def __init__ (self, future = None):
        Future.__init__ (self, MutableWait (), MutableCancel ())
        self.Replace (future)

    def Replace (self, future = None):
        if future is not None:
            self.wait.Replace (future.Wait)
            self.cancel.Replace (future.Cancel)
        else:
            self.wait.Replace ()
            self.cancel.Replace ()

#------------------------------------------------------------------------------#
# Unwrap Future                                                                #
#------------------------------------------------------------------------------#
class UnwrapFuture (MutableFuture):
    """Unwrap future helper"""
    __slots__ = MutableFuture.__slots__

    def __init__ (self, future):
        MutableFuture.__init__ (self, future)
        future.Continue (self.outer_cont)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def outer_cont (self, future):
        error = future.Error ()
        if error is None:
            inner_future = future.Result ()
            self.Replace (inner_future)
            inner_future.Continue (self.inner_cont)
        else:
            self.Replace ()
            self.ErrorSet (error)

    def inner_cont (self, future):
        self.Replace ()
        error = future.Error ()
        if error is None:
            self.ResultSet (future.Result ())
        else:
            self.ErrorSet (error)

#------------------------------------------------------------------------------#
# Continue With Async Future                                                   #
#------------------------------------------------------------------------------#
class ContinueWithAsyncFuture (MutableFuture):
    __slots__ = Future.__slots__ + ('async',)

    def __init__ (self, future, async):
        self.async = async

        MutableFuture.__init__ (self, future)
        future.Continue (self.future_cont)

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def future_cont (self, future):
        error = future.Error ()
        if error is None:
            self.Replace (self.async (future.Result ()).Continue (self.async_cont))
        else:
            self.Replace ()
            self.ErrorSet (error)

    def async_cont (self, future):
        self.Replace ()
        error = future.Error ()
        if error is None:
            self.ResultSet (future.Result ())
        else:
            self.ErrorSet (error)

# vim: nu ft=python columns=120 :
