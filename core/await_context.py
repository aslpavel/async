import sys
import threading

from ..future import Future, FutureNotReady, FutureCanceled
from ..future.compat import Raise

__all__ = ('ContextAwaiter',)
#------------------------------------------------------------------------------#
# Context Await Object                                                         #
#------------------------------------------------------------------------------#
class ContextAwaiter (object):
    def __init__ (self, core):
        self.core = core

        # continuations
        self.conts = []
        self.conts_lock = threading.RLock ()

    #--------------------------------------------------------------------------#
    # Await                                                                    #
    #--------------------------------------------------------------------------#
    def Await (self, value = None):
        """Await core context

        Returned future is resolved inside core context, and can only be
        continued once.
        """
        return ContextFuture (self.schedule, value)

    #--------------------------------------------------------------------------#
    # Resolve                                                                  #
    #--------------------------------------------------------------------------#
    def Resolve (self):
        """Resolve continued context futures
        """
        with self.conts_lock:
            conts, self.conts = self.conts, []

        for cont in conts:
            cont (None) # resolve with specified value

    #--------------------------------------------------------------------------#
    # Timeout
    #--------------------------------------------------------------------------#
    def Timeout (self):
        """Timeout before next event
        """
        with self.conts_lock:
            return 0 if self.conts else -1

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def schedule (self, cont):
        """Schedule continuation
        """
        with self.conts_lock:
            self.conts.append (cont)
        self.core.Notify ()

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self, error = None):
        """Dispose await object
        """
        try:
            raise error or FutureCanceled ('Context await object has been disposed')
        except Exception:
            error = sys.exc_info ()

        with self.conts_lock:
            conts, self.conts = self.conts, []

        for cont in conts:
            cont (error) # resolve with error

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Context Future                                                               #
#------------------------------------------------------------------------------#
class ContextFuture (Future):
    """Context future

    Future can only be continue once and, once continued its schedule with
    schedule function.
    """
    __slots__ = ('schedule','state', 'value',)

    STATE_NONE = 0x0
    STATE_CONT = 0x1
    STATE_DONE = 0x2
    STATE_FAIL = 0x4

    def __init__ (self, schedule, value):
        self.schedule = schedule
        self.state = self.STATE_NONE
        self.value = value

    #--------------------------------------------------------------------------#
    # Future Interface                                                         #
    #--------------------------------------------------------------------------#
    def Continue (self, cont):
        """Continue future with continuation
        """
        if self.state & self.STATE_CONT:
            raise ValueError ('{} can not be continued twice'.format (type (self).__name__))
        self.state |= self.STATE_CONT

        def callback (error):
            if error is None:
                self.state |= self.STATE_DONE
            else:
                self.value = error
                self.state |= self.STATE_DONE | self.STATE_FAIL
            cont (self.value, error)

        self.schedule (callback)
        return self

    def IsCompleted (self):
        """Is future completed
        """
        return self.state & self.STATE_DONE

    def Result (self):
        """Result of the future
        """
        if self.state & self.STATE_DONE:
            if self.state & self.STATE_FAIL:
                Raise (*self.value)
            return self.value
        raise FutureNotReady ()

    def Error (self):
        """Error of the future if any
        """
        return self.value if self.state & self.STATE_FAIL else None
