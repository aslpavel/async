# -*- coding: utf-8 -*-

__all__ = ('Wait', 'DummyWait', 'RaiseWait', 'CompositeWait', 'MutableWait',)
#------------------------------------------------------------------------------#
# Wait                                                                         #
#------------------------------------------------------------------------------#
class WaitError (Exception): pass
class Wait (object):
    __slots__ = ('uid', 'wait',)

    def __init__ (self, uid, wait):
        self.wait = wait
        self.uid = (uid,)

    #--------------------------------------------------------------------------#
    # Wait                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self):
        self.wait (self.uid)

    def uids (self):
        return self.uid

#------------------------------------------------------------------------------#
# Dummy Wait                                                                   #
#------------------------------------------------------------------------------#
class DummyWait (Wait):
    __slots__ = Wait.__slots__

    def __init__  (self):
        Wait.__init__ (self, None, lambda uids: None)

#------------------------------------------------------------------------------#
# Raise Wait                                                                   #
#------------------------------------------------------------------------------#
class RaiseWait (object):
    __slots__ = ('error',)

    def __init__ (self, error):
        self.error = error

    #--------------------------------------------------------------------------#
    # Wait                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self):
        raise self.error

    def uids (self):
        raise self.error

    @property
    def wait (self):
        raise self.error

#------------------------------------------------------------------------------#
# Composite Wait (WaitAny)                                                     #
#------------------------------------------------------------------------------#
class CompositeWait (object):
    __slots__ = ('objs',)

    def __init__ (self, *objs):
        self.objs = set (objs)

    #--------------------------------------------------------------------------#
    # Add | Remove                                                             #
    #--------------------------------------------------------------------------#
    def Add (self, obj):
        self.objs.add (obj)

    def __iadd__ (self, obj):
        self.Add (obj)
        return self

    def Remove (self, obj):
        self.objs.discard (obj)

    def __isub__ (self, obj):
        self.Remove (obj)
        return self

    #--------------------------------------------------------------------------#
    # Wait                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self):
        prev, curr = None, self.uids ()
        while curr and curr != prev:
            self.wait (curr)
            prev, curr = curr, self.uids ()

    def uids (self):
        uids = set ()
        for obj in self.objs:
            uids.update (obj.uids ())
        return uids

    @property
    def wait (self):
        return self.objs [0].wait if self.objs else (lambda uids: None)

#------------------------------------------------------------------------------#
# Mutable Wait (WaitAll)                                                       #
#------------------------------------------------------------------------------#
class MutableWait (object):
    __slots__ = ('obj',)

    def __init__ (self, obj = None):
        self.obj = obj

    #--------------------------------------------------------------------------#
    # Replace Wait Object                                                      #
    #--------------------------------------------------------------------------#
    def Replace (self, obj = None):
        self.obj = obj

    #--------------------------------------------------------------------------#
    # Wait                                                                     #
    #--------------------------------------------------------------------------#
    def __call__ (self):
        while self.obj is not None:
            self.wait (self.uids ())

    def uids (self):
        return tuple () if self.obj is None else self.obj.uids ()
    
    @property
    def wait (self):
        return (lambda uids: None) if self.obj is None else self.obj.wait
# vim: nu ft=python columns=120 :
