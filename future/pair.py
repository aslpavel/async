# -*- coding: utf-8 -*-
import sys
from .future import Future, FutureNotReady, FutureCanceled

FLAG_NONE = 0x0
FLAG_DONE = 0x1
FLAG_FAIL = 0x2

__all__ = ('FutureSourcePair',)
#------------------------------------------------------------------------------#
# Future Source Pair                                                           #
#------------------------------------------------------------------------------#
def FutureSourcePair ():
    """Returns Future, FutureSource pair
    """
    context = [FLAG_NONE, None, []] # flags, value, continuations
    return SourceReceiver (context), SourceSender (context)

#------------------------------------------------------------------------------#
# Source Sender                                                                #
#------------------------------------------------------------------------------#
class SourceSender (object):
    __slots__ = ('context',)

    def __init__ (self, context):
        self.context = context

    #--------------------------------------------------------------------------#
    # Set Value                                                                #
    #--------------------------------------------------------------------------#
    def SetResult (self, result):
        """Set result
        """
        if not self.TrySetResult (result):
            raise ValueError ('Future has already been resolved')

    def SetError (self, error):
        """Set error
        """
        if not self.TrySetError (error):
            raise ValueError ('Future has already been resolved')

    def SetException (self, exception):
        """Set exception
        """
        if not self.TrySetException (exception):
            raise ValueError ('Future has already been resolved')

    def SetCanceled (self):
        """Set canceled
        """
        if not self.TrySetCanceled ():
            raise ValueError ('Future has already been resolved')

    #--------------------------------------------------------------------------#
    # Try Set Value                                                            #
    #--------------------------------------------------------------------------#
    def TrySetResult (self, result):
        """Try set result
        """
        context = self.context
        if context [0] & FLAG_DONE:
            return False

        context [0] |= FLAG_DONE
        context [1]  = result
        conts, context [2] = context [2], None
        for cont in conts:
            cont (result, None)

        return True

    def TrySetError (self, error):
        """Try set error
        """
        context = self.context
        if context [0] & FLAG_DONE:
            return False

        context [0] |= FLAG_DONE | FLAG_FAIL
        context [1]  = error
        conts, context [2] = context [2], None
        for cont in conts:
            cont (None, error)

        return True

    def TrySetException (self, exception):
        """Try set exception
        """
        try: raise exception
        except Exception:
            error = sys.exc_info ()

        return self.TrySetError (error)

    def TrySetCanceled (self):
        """Try set canceled
        """
        return self.TrySetException (FutureCanceled ())

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose object
        """
        self.TrySetCanceled ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Source Receiver                                                              #
#------------------------------------------------------------------------------#
class SourceReceiver (Future):
    __slots__ = Future.__slots__ + ('context',)

    def __init__ (self, context):
        self.context = context

    #--------------------------------------------------------------------------#
    # Awaiter                                                                  #
    #--------------------------------------------------------------------------#
    def IsCompleted (self):
        """Is awaiter completed
        """
        return self.context [0] & FLAG_DONE

    def OnCompleted (self, cont):
        """On awaiter completed
        """
        flags = self.context [0]
        if flags & FLAG_DONE:
            if flags & FLAG_FAIL:
                cont (None, self.context [1])
            else:
                cont (self.context [1], None)
        else:
            self.context [2].append (cont)

    def GetResult (self):
        """Get result
        """
        flags = self.context [0]
        if flags & FLAG_DONE:
            if flags & FLAG_FAIL:
                return None, self.context [1]
            else:
                return self.context [1], None
        raise FutureNotReady ()

# vim: nu ft=python columns=120 :
