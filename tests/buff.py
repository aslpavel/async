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

# vim: nu ft=python columns=120 :
