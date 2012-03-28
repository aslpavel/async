# -*- coding: utf-8 -*-

__all__ = ('Delegate',)
#------------------------------------------------------------------------------#
# Delegate                                                                     #
#------------------------------------------------------------------------------#
class Delegate (object):
    """Delegate decorator

    Convert asynchronous method to Delegate which if called calls
    asynchronous method synchronously and has special method Async to call
    decorated function
    """
    __slots__ = ('async',)

    def __init__ (self, async):
        self.async = async

    def __get__ (self, instance, owner):
        if instance is None:
            return self.async
        return BoundDelegate (self, instance)

    def __call__ (self, *args, **keys):
        future = self.async (*args, **keys)
        future.Wait ()
        return future.Result ()

    def Async (self, *args, **keys):
        return self.async (*args, **keys)

#------------------------------------------------------------------------------#
# Bound Delegate                                                               #
#------------------------------------------------------------------------------#
class BoundDelegate (object):
    __slots__ = ('base', 'instance')

    def __init__ (self, base, instance):
        self.base = base
        self.instance = instance

    def __call__ (self, *args, **keys):
        return self.base (self.instance, *args, **keys)

    def Async (self, *args, **keys):
        return self.base.Async (self.instance, *args, **keys)

# vim: nu ft=python columns=120 :
