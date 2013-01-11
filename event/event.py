# -*- coding: utf-8 -*-

from ..future.future import Future

__all__ = ('Event',)
#------------------------------------------------------------------------------#
# Event                                                                        #
#------------------------------------------------------------------------------#
class Event (object):
    __slots__ = ('handlers', 'handling',)

    def __init__ (self):
        self.handlers = []
        self.handling = False

    #--------------------------------------------------------------------------#
    # Fire                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self, *args):
        """Fire event
        """
        if self.handling:
            raise RuntimeError ('Event fired in its handler')

        try:
            self.handling = True

            handlers, self.handlers = self.handlers, []
            for handler in handlers:
                if handler (*args):
                    self.handlers.append (handler)
        finally:
            self.handling = False

    #--------------------------------------------------------------------------#
    # On                                                                #
    #--------------------------------------------------------------------------#
    def On (self, handler):
        """On handler

        Returns specified handler. If handler returned value is False it will
        be automatically unsubscripted.
        """
        self.handlers.append (handler)
        return handler

    def __iadd__ (self, handler):
        """On handler
        """
        self.On (handler)
        return self

    #--------------------------------------------------------------------------#
    # Off                                                              #
    #--------------------------------------------------------------------------#
    def Off (self, handler):
        """Off handler

        Preferred way to do un-subscription is to return False from handler.
        Returns True in case of successful un-subscription.
        """
        try:
            self.handlers.remove (handler)
            return True
        except ValueError:
            return False

    def __isub__ (self, handler):
        """Off handler
        """
        self.Off (handler)
        return self

    #--------------------------------------------------------------------------#
    # Awaitable                                                                #
    #--------------------------------------------------------------------------#
    def Await (self):
        """Get awaiter
        """
        return EventFuture (self)

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

#------------------------------------------------------------------------------#
# Event Future                                                                 #
#------------------------------------------------------------------------------#
class EventFuture (Future):
    """Event future
    """
    __slots__ = Future.__slots__ + ('event', 'value',)

    def __init__ (self, event):
        self.event = event
        self.value = None

        def complete (*args):
            self.value = args
            return False

        event.On (complete)

    #--------------------------------------------------------------------------#
    # Awaitable                                                                #
    #--------------------------------------------------------------------------#
    def IsCompleted (self):
        """Is completed
        """
        return self.value is not None

    def OnCompleted (self, cont):
        """On completed
        """
        if self.value is None:
            def cont_handler (*args):
                cont (args, None)
                return False
            self.event.On (cont_handler)
        else:
            cont (self.value, None)

    def GetResult (self):
        """Result
        """
        if self.value is None:
            raise ValueError ('Awaiter is not completed')
        return self.value, None

    #--------------------------------------------------------------------------#
    # Representation                                                           #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<EventFuture [value:{}] at {}>'.format (
            'not-completed' if self.value is None else ','.join (self.value), id (self))

    def __repr__ (self):
        """String representation
        """
        return str (self)

# vim: nu ft=python columns=120 :
