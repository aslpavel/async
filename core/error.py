# -*- coding: utf-8 -*-

__all__ = ('CoreError', 'CoreIOError', 'CoreDisconnectedError', 'CoreInvalidError')
#------------------------------------------------------------------------------#
# Errors                                                                       #
#------------------------------------------------------------------------------#
class CoreError (Exception): pass
class CoreIOError (CoreError): pass
class CoreDisconnectedError (CoreIOError): pass
class CoreInvalidError (CoreIOError): pass

# vim: nu ft=python columns=120 :
