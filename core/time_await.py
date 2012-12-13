import itertools
from heapq import heappush, heappop
from time import time

from ..future import FutureSourcePair, FutureCanceled

__all__ = ('TimeAwaiter',)
#------------------------------------------------------------------------------#
# Timer                                                                        #
#------------------------------------------------------------------------------#
class TimeAwaiter (object):
    """Timer await object
    """
    __slots__ = ('uid', 'queue',)

    def __init__ (self):
        self.uid = itertools.count ()
        self.queue = []

    #--------------------------------------------------------------------------#
    # Await                                                                    #
    #--------------------------------------------------------------------------#
    def Await (self, when, cancel = None):
        """Await time specified by when argument
        """
        future, source = FutureSourcePair ()
        if cancel:
            cancel.Await ().OnCompleted (lambda *_: source.TrySetCanceled ())

        heappush (self.queue, (when, next (self.uid), source, future))
        return future

    #--------------------------------------------------------------------------#
    # Resolve                                                                  #
    #--------------------------------------------------------------------------#
    def Resolve (self):
        """Resolve all pending event scheduled before time
        """
        if not self.queue:
            return

        effected = []
        curr_time = time ()
        while self.queue:
            sched_time, _, source, future = self.queue [0]
            if sched_time > curr_time:
                break
            heappop (self.queue)
            effected.append ((source, sched_time))

        # resolve effected sources
        for source, sched_time in effected:
            source.TrySetResult (sched_time)

    #--------------------------------------------------------------------------#
    # Timeout                                                                  #
    #--------------------------------------------------------------------------#
    def Timeout (self):
        """Timeout before next resolve
        """
        while self.queue:
            sched_time, _, source, future = self.queue [0]
            if not future.IsCompleted ():
                return max (0, sched_time - time ())

            heappop (self.queue)
            continue

        return -1

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self, error = None):
        """Dispose timer and resolve all pending events with specified error
        """
        error = error or FutureCanceled ('Time await object has been disposed')

        queue, self.queue = self.queue, []
        for entry in queue:
            entry [2].TrySetException (error)

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

# vim: nu ft=python columns=120 :
