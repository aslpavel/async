# -*- coding: utf-8 -*-
from ..future import FutureSourcePair, FutureCanceled

__all__ = ('Event',)
#------------------------------------------------------------------------------#
# Event                                                                        #
#------------------------------------------------------------------------------#
class Event (object):
    __slots__ = ('handlers',)

    def __init__ (self):
        self.handlers = []

    #--------------------------------------------------------------------------#
    # Fire                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self, *args):
        """Fire event
        """
        handlers, self.handlers = self.handlers, []
        for handler in handlers:
            if handler (*args):
                self.handlers.append (handler)

    #--------------------------------------------------------------------------#
    # Subscribe                                                                #
    #--------------------------------------------------------------------------#
    def Subscribe (self, handler):
        """Subscribe handler

        Returns specified handler. If handler returned value is False it will
        be automatically unsubscripted.
        """
        self.handlers.append (handler)
        return handler

    def __iadd__ (self, handler):
        """Subscribe handler
        """
        self.Subscribe (handler)
        return self

    #--------------------------------------------------------------------------#
    # Unsubscribe                                                              #
    #--------------------------------------------------------------------------#
    def Unsubscribe (self, handler):
        """Unsubscribe handler

        Preferred way to do un-subscription is to return False from handler.
        Returns True in case of successful un-subscription.
        """
        try:
            self.handlers.remove (handler)
            return True
        except ValueError:
            return False

    def __isub__ (self, handler):
        """Unsubscribe handler
        """
        self.Unsubscribe (handler)
        return self

    #--------------------------------------------------------------------------#
    # Await                                                                    #
    #--------------------------------------------------------------------------#
    def Await (self, cancel = None):
        """Asynchronously await next event
        """
        future, source = FutureSourcePair ()

        # handler
        def handler (*args):
            source.SetResult (args)
            return False
        self.Subscribe (handler)

        # cancel
        if cancel:
            def cancel_cont (result, error):
                self.Unsubscribe (handler)
                source.SetCanceled ()
            cancel.Await ().OnCompleted (cancel_cont)

        return future

    #--------------------------------------------------------------------------#
    # Representation                                                           #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<{} at {}>'.format (type (self).__name__, id (self))

    def __repr__ (self):
        """String representation
        """
        return str (self)

# vim: nu ft=python columns=120 :
