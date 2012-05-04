# -*- coding: utf-8 -*-

__all__ = ('CoreError', 'CoreStopped', 'CoreIOError', 'CoreDisconnectedError', 'CoreInvalidError')
#------------------------------------------------------------------------------#
# Errors                                                                       #
#------------------------------------------------------------------------------#
class CoreError (Exception): pass
class CoreStopped (CoreError): pass
class CoreIOError (CoreError): pass
class CoreDisconnectedError (CoreIOError): pass
class CoreInvalidError (CoreIOError): pass

# vim: nu ft=python columns=120 :
