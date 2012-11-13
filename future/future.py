# -*- coding: utf-8 -*-
import io
import sys
import traceback
if sys.version_info [0] > 2:
    string_type = io.StringIO
else:
    string_type = io.BytesIO

from .compat import Raise

__all__ = ('Future', 'SucceededFuture', 'FailedFuture', 'RaisedFuture',
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
    # Continuation                                                             #
    #--------------------------------------------------------------------------#
    def __rshift__ (self, continuation):
        """Same as Continue
        """
        return self.Continue (continuation)

    def Continue (self, continuation):
        """Continue with continuation

        Result and Error are passed as arguments of the continuation.
        """
        raise NotImplementedError ()

    def ContinueSafe (self, continuation):
        """Continue with continuation

        Result and Error are passed as arguments of the continuation. If
        continuation raised an error its caught.
        """
        def continuation_safe (result, error):
            try:
                return continuation (result, error)
            except Exception: pass

        return self.Continue (continuation_safe)

    def ContinueSelf (self, continuation):
        """Continue with continuation

        Resolved future is passed as only argument of the continuation.
        """
        return self.Continue (lambda *_: continuation (self))

    def __ge__ (self, continuation):
        """Same as ContinueWith
        """
        return self.ContinueWith (continuation)

    def ContinueWith (self, continuation):
        """Continue with continuation

        Result and Error are passed as arguments of the continuation. Returns
        new future with result of the continuation.
        """
        if self.IsCompleted ():
            try:
                error = self.Error ()
                return SucceededFuture (continuation (self.Result (), None)
                    if error is None else continuation (None, error))
            except Exception:
                return FailedFuture (sys.exc_info ())

        source = FutureSource ()

        def continuation_with (result, error):
            try:
                source.ResultSet (continuation (result, error))
            except Exception:
                source.ErrorSet (sys.exc_info ())

        self.Continue (continuation_with)
        return source.Future

    def ContinueWithResult (self, continuation):
        """Continue with function

        Result of resolved future is passed as only argument of the function.
        Returns new future with result of function.
        """
        if self.IsCompleted ():
            error = self.Error ()
            if error is None:
                try:
                    return SucceededFuture (continuation (self.Result ()))
                except Exception:
                    return FailedFuture (sys.exc_info ())
            else:
                return FailedFuture (error)

        source = FutureSource ()

        def continuation_with (result, error):
            if error is None:
                try:
                    source.ResultSet (continuation (result))
                except Exception:
                    source.ErrorSet (sys.exc_info ())
            else:
                return source.ErrorSet (error)

        self.Continue (continuation_with)
        return source.Future

    #--------------------------------------------------------------------------#
    # Result                                                                   #
    #--------------------------------------------------------------------------#
    def Result (self):
        """Result of the future

        Return result of the future. If future is not resolved raises
        FutureNotReady exception. If future was resolved with error raises
        this error
        """
        raise NotImplementedError ()

    def Error (self):
        """Error of the future if any

        Returns tuple (ErrorType, ErrorObject, Traceback) if future was resolved
        with error None otherwise.
        """
        raise NotImplementedError ()

    def IsCompleted (self):
        """Future is completed
        """
        raise NotImplementedError ()

    #--------------------------------------------------------------------------#
    # Composition                                                              #
    #--------------------------------------------------------------------------#
    @staticmethod
    def WhenAny (futures):
        """Any future

        Returns future witch will be resolved with the first resolved future
        from future set.
        """
        futures = tuple (futures)
        source  = FutureSource ()

        for future in futures:
            future.ContinueSelf (lambda future: source.ResultSet (future))
            if source.Future.IsCompleted ():
                break

        return source.Future

    @staticmethod
    def WhenAll (futures):
        """All future

        Returns future witch will be resolved with None, if all futures was
        successfully completed, otherwise with the same error as the first
        unsuccessful future.
        """
        futures = tuple (futures)
        source = FutureSource ()

        count = [len (futures)]
        def continuation (result, error):
            if error is None:
                if count [0] == 1:
                    source.ResultSet (None)
                else:
                    count [0] -= 1
            else:
                source.ErrorSet (error)

        for future in futures:
            future.Continue (continuation)

        return source.Future

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __repr__ (self):
        """String representation of the future
        """
        return self.__str__ ()

    def __str__  (self):
        """String representation of the future
        """
        addr = id (self)
        name = type (self).__name__

        if self.IsCompleted ():
            error = self.Error ()
            if error is None:
                return '<{}[={}] at {}>'.format (name, self.Result (), addr)
            else:
                return '<{}[~{}: {}] at {}>'.format (name, error [0].__name__, error [1], addr)
        else:
            return '<{}[?] at {}>'.format (name, addr)

    #--------------------------------------------------------------------------#
    # Traceback                                                                #
    #--------------------------------------------------------------------------#
    def Traceback (self, name = None, file = None):
        """Print traceback when and only when future was resolved with error
        """
        file = file or sys.stderr

        def continuation (result, error):
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

        self.Continue (continuation)
        return self

#------------------------------------------------------------------------------#
# Succeeded Futures                                                            #
#------------------------------------------------------------------------------#
class SucceededFuture (Future):
    """Future resolve wit result
    """
    __slots__ = ('result',)

    def __init__ (self, result):
        self.result = result

    #--------------------------------------------------------------------------#
    # Continuation                                                             #
    #--------------------------------------------------------------------------#
    def Continue (self, continuation):
        continuation (self.result, None)
        return self

    def ContinueWith (self, continuation):
        try:
            return SucceededFuture (continuation (self.result, None))
        except Exception:
            return FailedFuture (sys.exc_info ())

    #--------------------------------------------------------------------------#
    # Result                                                                   #
    #--------------------------------------------------------------------------#
    def Result (self):
        return self.result

    def Error (self):
        return None

    def IsCompleted (self):
        return True

#------------------------------------------------------------------------------#
# Failed Future                                                                #
#------------------------------------------------------------------------------#
class FailedFuture (Future):
    """Future resolved with error
    """
    __slots__ = ('error',)

    def __init__ (self, error):
        self.error = error

    #--------------------------------------------------------------------------#
    # Continuation                                                             #
    #--------------------------------------------------------------------------#
    def Continue (self, continuation):
        continuation (None, self.error)
        return self

    def ContinueWith (self, continuation):
        return self

    #--------------------------------------------------------------------------#
    # Result                                                                   #
    #--------------------------------------------------------------------------#
    def Result (self):
        Raise (*self.error)

    def Error (self):
        return self.error

    def IsCompleted (self):
        return True

#------------------------------------------------------------------------------#
# Raised Future                                                                #
#------------------------------------------------------------------------------#
class RaisedFuture (FailedFuture):
    """Future resolved with error
    """
    __slots__ = FailedFuture.__slots__

    def __init__ (self, exception):
        try: raise exception
        except Exception:
            FailedFuture.__init__ (self, sys.exc_info ())

#------------------------------------------------------------------------------#
# Dependant Types                                                              #
#------------------------------------------------------------------------------#
from .source import FutureSource

# vim: nu ft=python columns=120 :
