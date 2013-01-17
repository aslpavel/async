# -*- coding: utf-8 -*-
from . import poll, error, core

from .poll import *
from .error import *
from .core import *

__all__ = poll.__all__ + error.__all__ + core.__all__ + (
          'Time', 'TimeDelay', 'Idle', 'Poll',)

#------------------------------------------------------------------------------#
# Convenience Functions                                                        #
#------------------------------------------------------------------------------#
def Time (time, cancel = None, core = None):
    """Resolved when specified unix time is reached

    Result of the future is scheduled time or FutureCanceled if it was canceled.
    """
    return (core or Core.Instance ()).Time (time, cancel)

def TimeDelay (delay, cancel = None, core = None):
    """Resolved after specified delay in seconds

    Result of the future is scheduled time.
    """
    return (core or Core.Instance ()).TimeDelay (delay, cancel)

def Idle (cancel = None, core = None):
    """Resolved when new iteration of the core is started.

    Result of the future is None of FutureCanceled if it was canceled.
    """
    return (core or Core.Instance ()).Idle (cancel)

def Poll (fd, mask, cancel = None, core = None):
    """Poll file descriptor

    Poll file descriptor for events specified by mask. If mask is None then
    specified descriptor is unregistered and all pending events are resolved
    with BrokenPipeError, otherwise future is resolved with bitmap of
    the events happened of file descriptor or error if any.
    """
    return (core or Core.Instance ()).Poll (fd, mask, cancel)

# vim: nu ft=python columns=120 :
