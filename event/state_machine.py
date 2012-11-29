# -*- coding: utf-8 -*-
from .event import Event

__all__ = ('StateMachine', 'StateMachineGraph',)
#------------------------------------------------------------------------------#
# State Machine                                                                #
#------------------------------------------------------------------------------#
class StateMachine (object):
    """State machine
    """
    __slots__ = ('graph', 'state', 'trans',)

    ERROR_TRANS = object ()

    def __init__ (self, graph):
        self.graph = graph

        self.state = graph.Initial
        self.trans = {trans: None for trans in graph}

    #--------------------------------------------------------------------------#
    # State                                                                    #
    #--------------------------------------------------------------------------#
    @property
    def State (self):
        return self.state

    #--------------------------------------------------------------------------#
    # Move                                                                     #
    #--------------------------------------------------------------------------#
    def Move (self, state, *args):
        """Make transition to specified state
        """
        return self (state, *args)

    def __call__ (self, state, *args):
        """Make transition to specified state

        In case of invalid transition ValueError is raised, if state machine
        already in desired state False is returned, otherwise state is changed
        and True is returned.
        """
        if self.state == state:
            return False

        trans = self.trans.get ((self.state, state), self.ERROR_TRANS)
        if trans is self.ERROR_TRANS:
            raise ValueError ('Invalid transition: {} -> {}'.format (self.state, state))

        self.state = state
        if trans is not None:
            trans (self.state, state, *args)

        return True

    #--------------------------------------------------------------------------#
    # Reset                                                                    #
    #--------------------------------------------------------------------------#
    def Reset (self):
        """Reset state machine
        """
        self.state = self.graph.Initial

    #--------------------------------------------------------------------------#
    # Subscribe                                                                #
    #--------------------------------------------------------------------------#
    def Subscribe (self, src, dst, handler):
        """Subscribe handler to the specified transition
        """
        return self.Event (src, dst).Subscribe (handler)

    #--------------------------------------------------------------------------#
    # Unsubscribe                                                              #
    #--------------------------------------------------------------------------#
    def Unsubscribe (self, src, dst, handler):
        """Unsubscribe handler from the specified transition
        """
        trans = self.trans.get ((src, dst), self.ERROR_TRANS)
        if trans is self.ERROR_TRANS:
            raise ValueError ('Invalid transition: {} -> {}'.format (src, dst))

        if trans is None:
            return False
        return trans.Unsubscribe (handler)

    #--------------------------------------------------------------------------#
    # Await                                                                    #
    #--------------------------------------------------------------------------#
    def Await (self, src, dst, cancel = None):
        """Await for the specified transition
        """
        return self.Event (src, dst).Await (cancel)

    #--------------------------------------------------------------------------#
    # Event                                                                    #
    #--------------------------------------------------------------------------#
    def Event (self, src, dst):
        """Get event for the specified transition
        """
        trans = self.trans.get ((src, dst), self.ERROR_TRANS)
        if trans is self.ERROR_TRANS:
            raise ValueError ('Invalid transition: {} -> {}'.format (src, dst))

        if trans is None:
            trans = Event ()
            self.trans [(src, dst)] = trans

        return trans

    #--------------------------------------------------------------------------#
    # Representation                                                           #
    #--------------------------------------------------------------------------#
    def __str__ (self):
        """String representation
        """
        return '<StateMachine [state:{}] at {}>'.format (self.state, id (self))

    def __repr__ (self):
        """String representation
        """
        return str (self)

#------------------------------------------------------------------------------#
# State Machine Graph                                                          #
#------------------------------------------------------------------------------#
class StateMachineGraph (set):
    """State machine graph
    """
    __slots__ = ('initial',)

    def __init__ (self, initial, trans):
        set.__init__ (self, trans)
        self.initial = initial

    #--------------------------------------------------------------------------#
    # Factories                                                                #
    #--------------------------------------------------------------------------#
    @classmethod
    def FromDict (cls, initial, dct):
        """Create graph from dictionary representation

        Dictionary with state as key and available transition states as its
        values. State must by hash-able and not None object.

        States graph example:
        {
            'initial':    ('connecting', 'disposed',),
            'connecting': ('connected', 'disposed',),
            'connected':  ('disposed',)
        }
        """
        trans = []
        initial_found = False
        for src, dsts in dct.items ():
            for dst in dsts:
                if src == initial:
                    initial_found = True
                trans.append ((src, dst))

        if not initial_found:
            raise ValueError ('Initial state does not have available transitions')

        return cls (initial, trans)

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Initial (self):
        return self.initial

# vim: nu ft=python columns=120 :
