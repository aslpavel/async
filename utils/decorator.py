# -*- coding: utf-8 -*-

__all__ = ('Decorator',)
#------------------------------------------------------------------------------#
# Decorator                                                                    #
#------------------------------------------------------------------------------#
class Decorator (object):
    __slots__ = tuple ()

    def __get__ (self, instance, owner):
        if instance is None:
            return self
        return self.BoundDecorator (self, instance)

    def __call__ (self, *args, **keys):
        raise NotImplementedError ()

    class BoundDecorator (object):
        __slots__ = ('unbound', 'instance')
        def __init__ (self, unbound, instance):
            self.unbound, self.instance = unbound, instance

        def __call__ (self, *args, **keys):
            return self.unbound (self.instance, *args, **keys)

        def __getattr__ (self, attr):
            return getattr (self.unbound, attr)

# vim: nu ft=python columns=120 :
