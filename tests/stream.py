# -*- coding: utf-8 -*-
import io
import re
import unittest
import collections

from . import AsyncTest
from ..async import Async, AsyncReturn
from ..future import FutureSource

from ..core.error import BrokenPipeError
from ..core.core import Core
from ..core.stream import AsyncStream
from ..core.buffer import Buffer

#------------------------------------------------------------------------------#
# Stream Test                                                                  #
#------------------------------------------------------------------------------#
class StreamTest (unittest.TestCase):
    """Test asynchronous stream
    """

    def testRead (self):
        stream = TestStream (8)

        read = stream.Read (6)
        self.assertFalse (read.IsCompleted ())
        self.assertEqual (stream.ReadComplete (b'012'), 3)
        self.assertEqual (read.Result (), b'012')

        read = stream.Read (3)
        self.assertFalse (read.IsCompleted ())
        self.assertEqual (stream.ReadComplete (b'012345'), 6)
        self.assertEqual (read.Result (), b'012')
        self.assertEqual (stream.Read (6).Result (), b'345')

        read = stream.Read (3)
        self.assertFalse (read.IsCompleted ())
        self.assertEqual (stream.ReadComplete (b'0123456789'), 8)
        self.assertEqual (read.Result (), b'012')
        self.assertEqual (stream.Read (6).Result (), b'34567')

        read = stream.Read (1)
        stream.ReadComplete (None)
        with self.assertRaises (BrokenPipeError):
            read.Result ()

    def testReadExactly (self):
        stream = TestStream (8)

        read = stream.ReadExactly (10)
        self.assertEqual (stream.ReadComplete (b'0123456789'), 8)
        self.assertFalse (read.IsCompleted (), False)
        self.assertEqual (stream.ReadComplete (b'0123456789'), 8)
        self.assertEqual (read.Result (), b'0123456701')

        read = stream.ReadExactly (4)
        self.assertEqual (read.Result (), b'2345')

    def testReadAll (self):
        stream = TestStream (1024)

        read = stream.ReadAll ()
        stream.ReadComplete (b'01234')
        stream.ReadComplete (b'56789')
        self.assertEqual (read.IsCompleted (), False)
        stream.ReadComplete (None)
        self.assertEqual (read.Result (), b'0123456789')

    def testReadFind (self):
        stream = TestStream (8)

        read = stream.ReadFind (b';')
        self.assertEqual (stream.ReadComplete (b'01234'), 5)
        self.assertFalse (read.IsCompleted (), False)
        self.assertEqual (stream.ReadComplete (b'56789;01'), 8)
        self.assertEqual (read.Result (), b'0123456789;')

        read = stream.ReadFind (b';')
        self.assertFalse (read.IsCompleted (), False)
        self.assertEqual (stream.ReadComplete (b'234;'), 4)
        self.assertEqual (read.Result (), b'01234;')

    def testReadFindRegex (self):
        stream = TestStream (1024)
        regex  = re.compile (br'([^=]+)=([^&]+)&')

        read = stream.ReadFindRegex (regex)
        stream.ReadComplete (b'key_0=')
        self.assertFalse (read.IsCompleted (), False)
        stream.ReadComplete (b'value_0&key_1')
        self.assertEqual (read.Result () [0], b'key_0=value_0&')

        read = stream.ReadFindRegex (regex)
        self.assertFalse (read.IsCompleted (), False)
        stream.ReadComplete (b'=value_1&tail')
        self.assertEqual (read.Result () [0], b'key_1=value_1&')

        read = stream.Read (4)
        self.assertEqual (read.Result (), b'tail')

    def testWrite (self):
        stream = TestStream (8)

        stream.Write (b'0123456')
        stream.WriteComplete (10)
        self.assertEqual (stream.Written, b'')

        stream.Write (b'7') # flusher started
        stream.Write (b'89')
        stream.WriteComplete (10)
        self.assertEqual (stream.Written, b'01234567')

        stream.WriteComplete (2)
        self.assertEqual (stream.Written, b'0123456789')

    def testMsg (self):
        stream = TestStream (1024)

        msg = b'from', b'to', b'body'

        stream.WriteMsg (*msg)
        stream.Flush ()
        stream.WriteComplete (1024)
        msg_data = stream.Written

        msg_future = stream.ReadMsg ()
        for index in range (len (msg_data)):
            self.assertFalse (msg_future.IsCompleted ())
            self.assertEqual (stream.ReadComplete (msg_data [index:index + 1]), 1)
        self.assertEqual (msg_future.Result (), msg)

#------------------------------------------------------------------------------#
# Test Stream                                                                  #
#------------------------------------------------------------------------------#
class TestStream (AsyncStream):
    """Asynchronous test stream
    """
    def __init__ (self, buffer_size):
        AsyncStream.__init__ (self, buffer_size)

        self.rd = Event ()
        self.rd_buffer = collections.deque ()

        self.wr = Event ()
        self.wr_buffer = io.BytesIO ()

        self.disposed = False
        
    #--------------------------------------------------------------------------#
    # Read                                                                     #
    #--------------------------------------------------------------------------#
    @Async
    def ReadRaw (self, size, cancel = None):
        if self.disposed:
            raise RuntimeError ('Stream has been disposed')

        self.rd_buffer.append (size)
        data = yield self.rd.Await ()
        if data is None:
            raise BrokenPipeError ()

        AsyncReturn (data)

    def ReadComplete (self, data):
        assert data is None or len (data) > 0

        if not self.rd_buffer:
            return

        elif data is None:
            self.rd (None)
            return None

        else:
            size = self.rd_buffer.popleft ()
            self.rd (data [:size])
            return min (len (data), size)

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    @Async
    def WriteRaw (self, data, cancel = None):
        if self.disposed:
            raise RuntimeError ('Stream has been disposed')

        size = yield self.wr.Await ()
        if size is None:
            raise BrokenPipeError ()

        self.wr_buffer.write (data [:size])
        AsyncReturn (min (len (data), size))

    @property
    def Written (self):
        return self.wr_buffer.getvalue ()

    def WriteComplete (self, size):
        assert size is None or size > 0
        self.wr (size)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def DisposeRaw (self):
        self.disposed = True

#------------------------------------------------------------------------------#
# Event                                                                        #
#------------------------------------------------------------------------------#
class Event (object):
    """Event

    Simplified "pretzel" event type.
    """
    def __init__ (self):
        self.handlers = set ()

    def __call__ (self, event):
        for handler in tuple (self.handlers):
            if handler (event):
                continue
            self.handlers.discard (handler)

    def Add (self, handler):
        self.handlers.add (handler)
        return handler

    def Remove (self, handler):
        self.handlers.discard (handler)

    def Await (self, cancel = None):
        source = FutureSource ()

        def handler (event):
            source.ResultSet (event)
            return False
        self.Add (handler)

        if cancel:
            def cancel_cont (result, error):
                self.Remove (handler)
                source.ErrorRaise (FutureCanceled ())
            cancel.Continue (cancel_cont)

        return source.Future

# vim: nu ft=python columns=120 :
