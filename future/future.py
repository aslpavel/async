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
    __slots__ = tuple ()

    def __init__ (self):
        if type (self) == Future:
            raise TypeError ('Future is an abstract class')

    #--------------------------------------------------------------------------#
    # Continuation                                                             #
    #--------------------------------------------------------------------------#
    def Continue (self, continuation):
        raise NotImplementedError ()

    def ContinueSafe (self, continuation):
        def continuation_safe (future):
            try:
                continuation (future)
            except Exception: pass

        self.Continue (continuation_safe)

    def ContinueWith (self, continuation):
        if self.IsCompleted ():
            try:
                return SucceededFuture (continuation (self))
            except Exception:
                return FailedFuture (sys.exc_info ())

        source = FutureSource ()

        def continuation_with (future):
            try:
                source.ResultSet (continuation (future))
            except Exception:
                source.ErrorSet (sys.exc_info ())

        self.Continue (continuation_with)
        return source.Future

    def ContinueWithFunction (self, func):
        if self.IsCompleted ():
            error = self.Error ()
            if error is None:
                try:
                    return SucceededFuture (func (self.Result ()))
                except Exception:
                    return FailedFuture (sys.exc_info ())
            else:
                return FailedFuture (error)

        source = FutureSource ()

        def continuation_with (future):
            error = self.Error ()
            if error is None:
                try:
                    source.ResultSet (func (future.Result ()))
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
        raise NotImplementedError ()

    def Error (self):
        raise NotImplementedError ()

    def IsCompleted (self):
        raise NotImplementedError ()

    #--------------------------------------------------------------------------#
    # Composition                                                              #
    #--------------------------------------------------------------------------#
    @staticmethod
    def WhenAny (futures):
        futures = tuple (futures)
        source  = FutureSource ()

        for future in futures:
            future.ContinueSafe (lambda resolved_future: source.ResultSet (resolved_future))
            if source.Future.IsCompleted ():
                break

        return source.Future

    @staticmethod
    def WhenAll (futures):
        def wait_all ():
            for future in tuple (futures):
                yield future

        return Async (wait_all) ()

    #--------------------------------------------------------------------------#
    # To String                                                                #
    #--------------------------------------------------------------------------#
    def __repr__ (self): return self.__str__ ()
    def __str__  (self):
        if self.IsCompleted ():
            error = self.Error ()
            if error is None:
                return '|> {} {}|'.format (self.Result (), id (self))
            else:
                return '|~ {}: {} {}|'.format (error [0].__name__, error [1], id (self))
        else:
            return '|? None {}|'.format (id (self))

    #--------------------------------------------------------------------------#
    # Traceback                                                                #
    #--------------------------------------------------------------------------#
    def Traceback (self, name = None, file = None):
        file = file or sys.stderr

        def continuation (future):
            try:
                return future.Result ()
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
    __slots__ = ('result',)

    def __init__ (self, result):
        self.result = result

    #--------------------------------------------------------------------------#
    # Continuation                                                             #
    #--------------------------------------------------------------------------#
    def Continue (self, continuation):
        continuation (self)

    def ContinueWith (self, continuation):
        try:
            return SucceededFuture (continuation (self))
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
    __slots__ = ('error',)

    def __init__ (self, error):
        self.error = error

    #--------------------------------------------------------------------------#
    # Continuation                                                             #
    #--------------------------------------------------------------------------#
    def Continue (self, continuation):
        continuation (self)

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
    __slots__ = FailedFuture.__slots__

    def __init__ (self, exception):
        try: raise exception
        except Exception:
            FailedFuture.__init__ (self, sys.exc_info ())

#------------------------------------------------------------------------------#
# Dependant Types                                                              #
#------------------------------------------------------------------------------#
from .source import FutureSource
from ..async import Async

# vim: nu ft=python columns=120 :
