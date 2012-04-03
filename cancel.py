# -*- coding: utf-8 -*-

__all__ = ('Cancel', 'RaiseCancel', 'MutableCancel',)
#------------------------------------------------------------------------------#
# Cancel Base Object                                                           #
#------------------------------------------------------------------------------#
class BaseCancel (object):
    __slots__ = tuple ()

    #--------------------------------------------------------------------------#
    # Cancel                                                                   #
    #--------------------------------------------------------------------------#
    def Cancel (self):
        raise NotImplementedError ()

    def __call__ (self):
        self.Cancel ()

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def __enter__ (self):
        return self

    def __exit__ (self, *error):
        self.Cancel ()
        return False

    #--------------------------------------------------------------------------#
    # Status                                                                   #
    #--------------------------------------------------------------------------#
    def IsCanceled (self):
        raise NotImplementedError ()

    def __bool__ (self): return self.IsCanceled ()
    def __nonzero__(self): return self.IsCanceled ()

#------------------------------------------------------------------------------#
# Cancel Object                                                                #
#------------------------------------------------------------------------------#
class Cancel (BaseCancel):
    __slots__ = ('cancel',)

    def __init__ (self, cancel = None):
        self.cancel = cancel

    #--------------------------------------------------------------------------#
    # Cancel                                                                   #
    #--------------------------------------------------------------------------#
    def Cancel (self):
        if self.cancel is None:
            return
        cancel, self.cancel = self.cancel, None
        cancel ()

    #--------------------------------------------------------------------------#
    # Status                                                                   #
    #--------------------------------------------------------------------------#
    def IsCanceled (self):
        return self.cancel is None

#------------------------------------------------------------------------------#
# Raise Cancel                                                                 #
#------------------------------------------------------------------------------#
class RaiseCancel (BaseCancel):
    __slots__ = ('error',)

    def __init__ (self, error):
        self.error = error

    #--------------------------------------------------------------------------#
    # Cancel Interface                                                         #
    #--------------------------------------------------------------------------#
    def Cancel (self):
        raise self.error

    def IsCanceled (self):
        return True

#------------------------------------------------------------------------------#
# Mutable Cancel                                                               #
#------------------------------------------------------------------------------#
class MutableCancel (BaseCancel):
    __slots__ = ('cancel',)

    def __init__ (self, cancel = None):
        self.cancel = cancel

    #--------------------------------------------------------------------------#
    # Cancel Interface                                                         #
    #--------------------------------------------------------------------------#
    def Cancel (self):
        if self.cancel is not None:
            self.cancel.Cancel ()

    def IsCanceled (self):
        return False if self.cancel is None else self.cancel.IsCanceled ()

    #--------------------------------------------------------------------------#
    # Replace                                                                  #
    #--------------------------------------------------------------------------#
    def Replace (self, cancel = None):
        self.cancel = cancel

# vim: nu ft=python columns=120 :
