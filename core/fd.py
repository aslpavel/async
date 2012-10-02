# -*- coding: utf-8 -*-
import os
import fcntl

__all__ = ('FileBlocking', 'FileCloseOnExec')
#------------------------------------------------------------------------------#
# File Descriptor Options                                                      #
#------------------------------------------------------------------------------#
def FileBlocking (fd, enable = None):
    """Set file "blocking"

    If enable is not set, returns current "blocking" value.
    """
    return not fileOptions (fd, fcntl.F_GETFL, fcntl.F_SETFL, os.O_NONBLOCK,
        None if enable is None else not enable)

def FileCloseOnExec (fd, enable = None):
    """Set file "close on exec" value

    If enable is not set, returns current "close on exec" value.
    """
    return fileOptions (fd, fcntl.F_GETFD, fcntl.F_SETFD, fcntl.FD_CLOEXEC, enable)

#------------------------------------------------------------------------------#
# Helper                                                                       #
#------------------------------------------------------------------------------#
def fileOptions (fd, get_option, set_option, option, enable = None):
    """File option helper function
    """
    options = fcntl.fcntl (fd, get_option)
    if enable is None:
        return bool (options & option)
    elif enable:
        options |= option
    else:
        options &= ~option
    fcntl.fcntl (fd, set_option, options)
    return enable

# vim: nu ft=python columns=120 :
