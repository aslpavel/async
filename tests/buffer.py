# -*- coding: utf-8 -*-
import unittest

from ..stream.buff import Buffer

__all__ = ('BufferTest',)
#------------------------------------------------------------------------------#
# Buffer Test                                                                  #
#------------------------------------------------------------------------------#
class BufferTest (unittest.TestCase):
    """Buffer unit tests
    """

    def test (self):
        buf = Buffer ()

        buf.Put (b'01234')
        buf.Put (b'56789')
        buf.Put (b'01234')

        self.assertEqual (len (buf), 15)

        # single chunk
        self.assertEqual (buf.Peek (3), b'012')
        self.assertEqual (tuple (buf.chunks), (b'01234', b'56789', b'01234',))

        # cross chunk
        self.assertEqual (buf.Peek (6), b'012345')
        self.assertEqual (tuple (buf.chunks), (b'0123456789', b'01234',))

        # discard chunk
        buf.Discard (3)
        self.assertEqual (len (buf), 12)
        self.assertEqual (buf.offset, 3)
        self.assertEqual (tuple (buf.chunks), (b'0123456789', b'01234',))

        # with offset
        self.assertEqual (buf.Peek (3), b'345')
        self.assertEqual (tuple (buf.chunks), (b'0123456789', b'01234',))

        # discard cross chunk
        buf.Discard (8)
        self.assertEqual (len (buf), 4)
        self.assertEqual (buf.offset, 1)
        self.assertEqual (tuple (buf.chunks), (b'01234',))

        buf.Put (b'56789')
        buf.Put (b'01234')

        # cross chunks with offset
        self.assertEqual (buf.Peek (5), b'12345')
        self.assertEqual (tuple (buf.chunks), (b'0123456789', b'01234',))

        # peek all
        self.assertEqual (buf.Peek (128), b'12345678901234')
        self.assertEqual (tuple (buf.chunks), (b'012345678901234',))

        buf.Put (b'56789')

        # discard all
        buf.Discard (128)
        self.assertEqual (len (buf), 0)
        self.assertEqual (tuple (buf.chunks), tuple ())

        for _ in range (3):
            buf.Put (b'0123456789')

        # discard with chunk cut
        buf.Discard (6)
        self.assertEqual (len (buf), 24)
        self.assertEqual (buf.offset, 0)
        self.assertEqual (tuple (buf.chunks), (b'6789', b'0123456789', b'0123456789'))

        # discard edge
        buf.Discard (14)
        self.assertEqual (len (buf), 10)
        self.assertEqual (buf.offset, 0)
        self.assertEqual (tuple (buf.chunks), (b'0123456789',))

        # discard less then half
        buf.Discard (4)
        self.assertEqual (len (buf), 6)
        self.assertEqual (buf.offset, 4)
        self.assertEqual (tuple (buf.chunks), (b'0123456789',))

        # discard big
        buf.Discard (128)
        self.assertEqual (len (buf), 0)
        self.assertEqual (buf.offset, 0)
        self.assertEqual (tuple (buf.chunks), tuple ())

# vim: nu ft=python columns=120 :
