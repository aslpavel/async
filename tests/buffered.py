# -*- coding: utf-8 -*-
import io
import re
import errno
import struct
import unittest
import collections

from ..async import Async, AsyncReturn
from ..event import Event

from ..core import BrokenPipeError
from ..stream import Stream
from ..stream.buffered import Buffer, BufferedStream

__all__ = ('BufferTest', 'StreamTest',)
#------------------------------------------------------------------------------#
# Buffer Test                                                                  #
#------------------------------------------------------------------------------#
class BufferTest (unittest.TestCase):
    """Buffer unit tests
    """

    def test (self):
        buff = Buffer ()

        buff.Enqueue (b'01234')
        buff.Enqueue (b'56789')
        buff.Enqueue (b'01234')

        self.assertEqual (buff.Length (), 15)

        # single chunk
        self.assertEqual (buff.Slice (3), b'012')
        self.assertEqual (tuple (buff.chunks), (b'01234', b'56789', b'01234',))

        # cross chunk
        self.assertEqual (buff.Slice (6), b'012345')
        self.assertEqual (tuple (buff.chunks), (b'0123456789', b'01234',))

        # discard chunk
        buff.Dequeue (3)
        self.assertEqual (buff.Length (), 12)
        self.assertEqual (buff.offset, 3)
        self.assertEqual (tuple (buff.chunks), (b'0123456789', b'01234',))

        # with offset
        self.assertEqual (buff.Slice (3), b'345')
        self.assertEqual (tuple (buff.chunks), (b'0123456789', b'01234',))

        # discard cross chunk
        buff.Dequeue (8)
        self.assertEqual (buff.Length (), 4)
        self.assertEqual (buff.offset, 1)
        self.assertEqual (tuple (buff.chunks), (b'01234',))

        buff.Enqueue (b'56789')
        buff.Enqueue (b'01234')

        # cross chunks with offset
        self.assertEqual (buff.Slice (5), b'12345')
        self.assertEqual (tuple (buff.chunks), (b'0123456789', b'01234',))

        # peek all
        self.assertEqual (buff.Slice (128), b'12345678901234')
        self.assertEqual (tuple (buff.chunks), (b'012345678901234',))

        buff.Enqueue (b'56789')

        # discard all
        buff.Dequeue (128)
        self.assertEqual (buff.Length (), 0)
        self.assertEqual (tuple (buff.chunks), tuple ())

        for _ in range (3):
            buff.Enqueue (b'0123456789')

        # discard with chunk cut
        buff.Dequeue (6)
        self.assertEqual (buff.Length (), 24)
        self.assertEqual (buff.offset, 0)
        self.assertEqual (tuple (buff.chunks), (b'6789', b'0123456789', b'0123456789'))

        # discard edge
        buff.Dequeue (14)
        self.assertEqual (buff.Length (), 10)
        self.assertEqual (buff.offset, 0)
        self.assertEqual (tuple (buff.chunks), (b'0123456789',))

        # discard less then half
        buff.Dequeue (4)
        self.assertEqual (buff.Length (), 6)
        self.assertEqual (buff.offset, 4)
        self.assertEqual (tuple (buff.chunks), (b'0123456789',))

        # discard big
        buff.Dequeue (128)
        self.assertEqual (buff.Length (), 0)
        self.assertEqual (buff.offset, 0)
        self.assertEqual (tuple (buff.chunks), tuple ())

#------------------------------------------------------------------------------#
# Stream Test                                                                  #
#------------------------------------------------------------------------------#
class StreamTest (unittest.TestCase):
    """Test asynchronous stream
    """

    #--------------------------------------------------------------------------#
    # Read                                                                     #
    #--------------------------------------------------------------------------#
    def testRead (self):
        stream = BufferedStream (TestStream (), 8)

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

    def testReadUntilSize (self):
        stream = BufferedStream (TestStream (), 8)

        read = stream.ReadUntilSize (10)
        self.assertEqual (stream.ReadComplete (b'0123456789'), 8)
        self.assertFalse (read.IsCompleted (), False)
        self.assertEqual (stream.ReadComplete (b'0123456789'), 8)
        self.assertEqual (read.Result (), b'0123456701')

        read = stream.ReadUntilSize (4)
        self.assertEqual (read.Result (), b'2345')

    def testReadUntilEof (self):
        stream = BufferedStream (TestStream (), 1024)

        read = stream.ReadUntilEof ()
        stream.ReadComplete (b'01234')
        stream.ReadComplete (b'56789')
        self.assertEqual (read.IsCompleted (), False)
        stream.ReadComplete (None)
        self.assertEqual (read.Result (), b'0123456789')

    def testReadUntilSub (self):
        stream = BufferedStream (TestStream (), 8)

        read = stream.ReadUntilSub (b';')
        self.assertEqual (stream.ReadComplete (b'01234'), 5)
        self.assertFalse (read.IsCompleted (), False)
        self.assertEqual (stream.ReadComplete (b'56789;01'), 8)
        self.assertEqual (read.Result (), b'0123456789;')

        read = stream.ReadUntilSub (b';')
        self.assertFalse (read.IsCompleted (), False)
        self.assertEqual (stream.ReadComplete (b'234;'), 4)
        self.assertEqual (read.Result (), b'01234;')

    def testReadUntilRegex (self):
        stream = BufferedStream (TestStream (), 1024)
        regex  = re.compile (br'([^=]+)=([^&]+)&')

        read = stream.ReadUntilRegex (regex)
        stream.ReadComplete (b'key_0=')
        self.assertFalse (read.IsCompleted (), False)
        stream.ReadComplete (b'value_0&key_1')
        self.assertEqual (read.Result () [0], b'key_0=value_0&')

        read = stream.ReadUntilRegex (regex)
        self.assertFalse (read.IsCompleted (), False)
        stream.ReadComplete (b'=value_1&tail')
        self.assertEqual (read.Result () [0], b'key_1=value_1&')

        read = stream.Read (4)
        self.assertEqual (read.Result (), b'tail')

    #--------------------------------------------------------------------------#
    # Write                                                                    #
    #--------------------------------------------------------------------------#
    def testWrite (self):
        stream = BufferedStream (TestStream (), 8)

        stream.Write (b'0123456')
        stream.WriteComplete (10)
        self.assertEqual (stream.Written, b'')

        stream.Write (b'7') # flusher started
        stream.Write (b'89')
        stream.WriteComplete (10)
        self.assertEqual (stream.Written, b'01234567')

        stream.WriteComplete (2)
        self.assertEqual (stream.Written, b'0123456789')

    #--------------------------------------------------------------------------#
    # Serialize                                                                #
    #--------------------------------------------------------------------------#
    def testBytes (self):
        stream = BufferedStream (TestStream (), 1024)

        bytes = b'some bytes string'

        stream.BytesWriteBuffer (bytes)
        stream.Flush ()
        stream.WriteComplete (1024)

        bytes_future = stream.BytesRead ()
        stream.ReadComplete (stream.Written)
        self.assertEqual (bytes_future.Result (), bytes)

    def testStructList (self):
        stream = BufferedStream (TestStream (), 1024)

        struct_type = struct.Struct ('>H')
        struct_list = [23, 16, 10, 32, 45, 18]

        stream.StructListWriteBuffer (struct_list, struct_type)
        stream.Flush ()
        stream.WriteComplete (1024)

        struct_future = stream.StructListRead (struct_type)
        stream.ReadComplete (stream.Written)
        self.assertEqual (struct_future.Result (), struct_list)

    def testStructListComplex (self):
        stream = BufferedStream (TestStream (), 1024)

        struct_type = struct.Struct ('>HH')
        struct_list = [(23, 0), (16, 1), (10, 2), (32, 3), (45, 4), (18, 5)]

        stream.StructListWriteBuffer (struct_list, struct_type, True)
        stream.Flush ()
        stream.WriteComplete (1024)

        struct_future = stream.StructListRead (struct_type, True)
        stream.ReadComplete (stream.Written)
        self.assertEqual (struct_future.Result (), struct_list)

    def testBytesList (self):
        stream = BufferedStream (TestStream (), 1024)

        bytes_list = [b'one', b'two', b'three', b'four', b'five']

        stream.BytesListWriteBuffer (bytes_list)
        stream.Flush ()
        stream.WriteComplete (1024)

        bytes_list_future = stream.BytesListRead ()
        stream.ReadComplete (stream.Written)
        self.assertEqual (bytes_list_future.Result (), bytes_list)

#------------------------------------------------------------------------------#
# Test Stream                                                                  #
#------------------------------------------------------------------------------#
class TestStream (Stream):
    """Asynchronous test stream
    """
    def __init__ (self):
        Stream.__init__ (self)

        self.rd = Event ()
        self.rd_buffer = collections.deque ()

        self.wr = Event ()
        self.wr_buffer = io.BytesIO ()

    #--------------------------------------------------------------------------#
    # Read                                                                     #
    #--------------------------------------------------------------------------#
    @Async
    def Read (self, size, cancel = None):
        with self.reading:
            self.rd_buffer.append (size)
            data = (yield self.rd) [0]
            if data is None:
                raise BrokenPipeError (errno.EPIPE, 'Broken pipe')

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
    def Write (self, data, cancel = None):
        with self.writing:
            size = (yield self.wr) [0]
            if size is None:
                raise BrokenPipeError (errno.EPIPE, 'Broken pipe')

            self.wr_buffer.write (data [:size])
            AsyncReturn (min (len (data), size))

    @property
    def Written (self):
        return self.wr_buffer.getvalue ()

    def WriteComplete (self, size):
        assert size is None or size > 0
        self.wr (size)

# vim: nu ft=python columns=120 :
