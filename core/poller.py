# -*- coding: utf-8 -*-
import errno
import select

__all__ = ('Poller', 'EPollPoller', 'KQueuePoller', 'SelectPoller',)
#------------------------------------------------------------------------------#
# EPoll Constants                                                              #
#------------------------------------------------------------------------------#
EPOLLIN      = 0x001
EPOLLPRI     = 0x002
EPOLLOUT     = 0x004
EPOLLRDNORM  = 0x040
EPOLLRDBAND  = 0x080
EPOLLWRNORM  = 0x100
EPOLLWRBAND  = 0x200
EPOLLMSG     = 0x400
EPOLLERR     = 0x008
EPOLLHUP     = 0x010
EPOLLRDHUP   = 0x2000
EPOLLONESHOT = 1 << 30
EPOLLET      = 1 << 31

#------------------------------------------------------------------------------#
# Poller                                                                       #
#------------------------------------------------------------------------------#
class Poller (object):
    DEFAULT_NAME = 'epoll' if hasattr (select, 'epoll') else \
                   'kqueue' if hasattr (select, 'kqueue') else \
                   'select'

    READ       = EPOLLIN
    WRITE      = EPOLLOUT
    URGENT     = EPOLLPRI
    DISCONNECT = EPOLLHUP
    ERROR      = EPOLLERR | EPOLLHUP

    #--------------------------------------------------------------------------#
    # Factory                                                                  #
    #--------------------------------------------------------------------------#
    @classmethod
    def FromName (cls, name = None):
        name = name or cls.DEFAULT_NAME

        if name == 'epoll' and hasattr (select, 'epoll'):
            return EPollPoller ()
        elif name == 'kqueue' and hasattr (select, 'kqueue'):
            return KQueuePoller ()
        elif name == 'select':
            return SelectPoller ()

        raise NotImplementedError ('Poller method is not support: {}'.format (name))

    #--------------------------------------------------------------------------#
    # Poller Interface                                                         #
    #--------------------------------------------------------------------------#
    @property
    def Name (self):
        return 'virtual'

    def IsEmpty (self):
        raise NotImplementedError ()

    def Register (self, fd, mask):
        raise NotImplementedError ()

    def Modify (self, fd, mask):
        raise NotImplementedError ()

    def Unregister (self, fd):
        raise NotImplementedError ()

    def Poll (self, timeout):
        raise NotImplementedError ()

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        pass

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# EPoll Poller                                                                 #
#------------------------------------------------------------------------------#
class EPollPoller (Poller):
    def __init__ (self):
        self.fds   = {}
        self.epoll = select.epoll ()

        from ..stream.file import CloseOnExecFD
        CloseOnExecFD (self.epoll.fileno (), True)

    #--------------------------------------------------------------------------#
    # Poller Interface                                                         #
    #--------------------------------------------------------------------------#
    @property
    def Name (self):
        return 'epoll'

    def Register (self, fd, mask):
        self.epoll.register (fd, mask)
        self.fds.setdefault (fd, True)

    def Modify (self, fd, mask):
        self.epoll.modify (fd, mask)

    def Unregister (self, fd):
        if self.fds.pop (fd, None):
            self.epoll.unregister (fd)

    def Poll (self, timeout):
        if not self.fds and timeout < 0:
            raise StopIteration () # would have blocked indefinitely

        try:
            return self.epoll.poll (timeout)
        except IOError as error:
            if error.errno == errno.EINTR:
                return tuple ()
            raise

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.epoll.close ()

#------------------------------------------------------------------------------#
# Select Poller                                                                #
#------------------------------------------------------------------------------#
class SelectPoller (Poller):
    SUPPORTED_MASK = Poller.READ | Poller.WRITE

    def __init__ (self):
        self.read  = set ()
        self.write = set ()
        self.error = set ()

    #--------------------------------------------------------------------------#
    # Poller Interface                                                         #
    #--------------------------------------------------------------------------#
    @property
    def Name (self):
        return 'select'

    def Register (self, fd, mask):
        if mask | self.SUPPORTED_MASK != self.SUPPORTED_MASK:
            raise ValueError ('Unsupported event mask: {}'.format (mask))

        self.error.add (fd)
        if mask & Poller.READ:
            self.read.add (fd)
        if mask & Poller.WRITE:
            self.write.add (fd)

    def Modify (self, fd, mask):
        self.Unregister (fd)
        self.Register (fd)

    def Unregister (self, fd):
        self.read.discard (fd)
        self.write.discard (fd)
        self.error.discard (fd)

    def Poll (self, timeout):
        if not self.error and timeout < 0:
            raise StopIteration () # would have blocked indefinitely

        read, write, error = select.select (self.read, self.write, self.error,
            timeout if timeout >= 0 else None)

        events = {}
        for fd in read:
            events [fd] = events.get (fd, 0) | Poller.READ
        for fd in write:
            events [fd] = events.get (fd, 0) | Poller.WRITE
        for fd in error:
            events [fd] = events.get (fd, 0) | Poller.ERROR

        return events.items ()

#------------------------------------------------------------------------------#
# KQueue Poller                                                                #
#------------------------------------------------------------------------------#
class KQueuePoller (SelectPoller):
    pass

# vim: nu ft=python columns=120 :
