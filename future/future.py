# -*- coding: utf-8 -*-
import io
import sys
import traceback
if sys.version_info [0] > 2:
    string_type = io.StringIO
else:
    string_type = io.BytesIO

from .compat import Raise

__all__ = ('Future', 'CompletedFuture', 'SucceededFuture', 'FailedFuture', 'RaisedFuture',
    'FutureError', 'FutureNotReady', 'FutureCanceled')
#------------------------------------------------------------------------------#
# Future Errors                                                                #
#------------------------------------------------------------------------------#
class FutureError (Exception): pass
class FutureNotReady (FutureError): pass
class FutureCanceled (FutureError): pass

#------------------------------------------------------------------------------#
# Future                                                                       #
#------------------------------------------------------------------------------#
class Future (object):
    """Future object

    Future object is either resolved and contains result of the operation
    (value or exception) or unresolved and represents ongoing operation. In any
    case you can continue this object with continuation function witch will be
    called upon future being resolved or immediately if it has already been
    resolved.
    """
    __slots__ = tuple ()

    def __init__ (self):
        if type (self) == Future:
            raise TypeError ('Future is an abstract class')

    #--------------------------------------------------------------------------#
    # Awaitable                                                                #
    #--------------------------------------------------------------------------#
    def Await (self):
        """Get awaiter of awaitable object

        In case of future object awaiter object is future itself.
        """
        return self

    def IsCompleted (self):
        """Is future completed
        """
        raise NotImplementedError ()

    def OnCompleted (self, cont):
        """Call continuation when the awaiter is completed

        Result and error are passed as arguments of the continuation.
        """
        raise NotImplementedError ()

    def GetResult (self):
        """Get result of the awaiter

        Returns result-error pair.
        """
        raise NotImplementedError ()

    #--------------------------------------------------------------------------#
    # Then                                                                     #
    #--------------------------------------------------------------------------#
    def Then (self, cont):
        """Chain continuation

        Result and Error are passed as arguments of the continuation. Returns
        this future object as result.
        """
        self.OnCompleted (cont)
        return self

    #--------------------------------------------------------------------------#
    # Chain                                                                    #
    #--------------------------------------------------------------------------#
    def Chain (self, cont):
        """Chain continuation

        Result and Error are passed as arguments of the continuation. Returns
        new future with result of the continuation.
        """
        if self.IsCompleted ():
            try:
                return CompletedFuture (cont (*self.GetResult ()))
            except Exception:
                return CompletedFuture (error = sys.exc_info ())

        future, source = FutureSourcePair ()
        def chain_cont (result, error):
            try:
                source.SetResult (cont (result, error))
            except Exception:
                source.SetError (sys.exc_info ())
        self.OnCompleted (chain_cont)

        return future

    def ChainResult (self, cont):
        """Chain function

        Result of resolved future is passed as only argument of the function.
        Returns new future with result of function.
        """
        if self.IsCompleted ():
            result, error = self.GetResult ()
            if error is None:
                try:
                    return CompletedFuture (cont (result))
                except Exception:
                    return CompletedFuture (error = sys.exc_info ())
            else:
                return CompletedFuture (error = error)

        future, source = FutureSourcePair ()

        def chain_result_cont (result, error):
            if error is None:
                try:
                    source.SetResult (cont (result))
                except Exception:
                    source.SetError (sys.exc_info ())
            else:
                return source.SetError (error)
        self.OnCompleted (chain_result_cont)

        return future

    #--------------------------------------------------------------------------#
    # Result                                                                   #
    #--------------------------------------------------------------------------#
    def Result (self):
        """Result of the future

        Return result of the future. If future is not resolved raises
        FutureNotReady exception. If future was resolved with error raises
        this error
        """
        result, error = self.GetResult ()
        if error is None:
            return result
        else:
            Raise (*error)

    def Error (self):
        """Error of the future if any

        Returns tuple (ErrorType, ErrorObject, Traceback) if future was resolved
        with error None otherwise.
        """
        return self.GetResult () [1]

    #--------------------------------------------------------------------------#
    # Composition                                                              #
    #--------------------------------------------------------------------------#
    @staticmethod
    def Any (awaitables):
        """Any future

        Returns future witch will be resolved with the first resolved future
        from future set.
        """
        awaiters = tuple (awaitable.Await () for awaitable in awaitables)
        if not awaiters:
            return RaisedFuture (ValueError ('Awaitable set is empty'))

        future, source = FutureSourcePair ()

        def awaiter_register (awaiter):
            if awaiter.IsCompleted ():
                source.TryResultSet ()
            else:
                def any_cont (result, error):
                    source.TrySetResult (awaiter)
                awaiter.OnCompleted (any_cont)

        for awaiter in awaiters:
            awaiter_register (awaiter)

        return future


    @staticmethod
    def All (awaitables):
        """All future

        Returns future witch will be resolved with None, if all futures was
        successfully completed, otherwise with the same error as the first
        unsuccessful future.
        """
        awaiters = tuple (awaitable.Await () for awaitable in awaitables)
        if not awaiters:
            return RaisedFuture (ValueError ('Awaitable set is empty'))

        future, source = FutureSourcePair ()

        count = [len (awaiters)]
        def all_cont (result, error):
            if error is None:
                if count [0] == 1:
                    source.TrySetResult (None)
                else:
                    count [0] -= 1
            else:
                source.TrySetError (error)

        for awaiter in awaiters:
            awaiter.OnCompleted (all_cont)

        return future

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __str__  (self):
        """String representation of the future
        """
        addr = id (self)
        name = type (self).__name__

        if self.IsCompleted ():
            result, error = self.GetResult ()
            if error is None:
                return '<{} [={}] at {}>'.format (name, result, addr)
            else:
                return '<{} [~{}: {}] at {}>'.format (name, error [0].__name__, error [1], addr)
        else:
            return '<{} [?] at {}>'.format (name, addr)

    def __repr__ (self):
        """String representation of the future
        """
        return str (self)

    #--------------------------------------------------------------------------#
    # Traceback                                                                #
    #--------------------------------------------------------------------------#
    def Traceback (self, name = None, file = None):
        """Print traceback when and only when future was resolved with error
        """
        file = file or sys.stderr

        def cont (result, error):
            try:
                return self.Result ()
            except Exception as error:
                stream = string_type ()

                # header
                stream.write ('Future \'{}\' has terminated with error\n'.format (name or 'UNNAMED'))

                # traceback
                traceback.print_exc (file = stream)

                # saved traceback
                traceback_saved = getattr (error, '_saved_traceback', None)
                if traceback_saved is not None:
                    stream.write (traceback_saved)

                # output
                file.write (stream.getvalue ())
                file.flush ()

        return self.Then (cont)

#------------------------------------------------------------------------------#
# Completed Future                                                             #
#------------------------------------------------------------------------------#
class CompletedFuture (Future):
    """Completed future
    """
    __slots__ = Future.__slots__ + ('value',)

    def __init__ (self, result = None, error = None):
        self.value = result, error

    #--------------------------------------------------------------------------#
    # Awaiter                                                                  #
    #--------------------------------------------------------------------------#
    def IsCompleted (self):
        return True

    def OnCompleted (self, cont):
        cont (*self.value)

    def GetResult (self):
        return self.value

def SucceededFuture (result):
    """Future resolved with result
    """
    return CompletedFuture (result)

def FailedFuture (error):
    """Future resolved with error
    """
    return CompletedFuture (error = error)

def RaisedFuture (exception):
    """Future resolved with error from provided exception
    """
    try: raise exception
    except Exception:
        return CompletedFuture (error = sys.exc_info ())

#------------------------------------------------------------------------------#
# Dependant Types                                                              #
#------------------------------------------------------------------------------#
from .pair import FutureSourcePair

# vim: nu ft=python columns=120 :
