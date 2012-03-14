# -*- coding: utf-8 -*-

__all__ = ('CoreError', 'CoreIOError', 'CoreHUPError', 'CoreNVALError')
#------------------------------------------------------------------------------#
# Errors                                                                       #
#------------------------------------------------------------------------------#
class CoreError (Exception): pass
class CoreIOError (CoreError): pass
class CoreHUPError (CoreIOError): pass
class CoreNVALError (CoreIOError): pass

# vim: nu ft=python columns=120 :
