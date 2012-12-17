# -*- coding: utf-8 -*-
import unittest

from ..event import Event

#------------------------------------------------------------------------------#
# Event                                                                        #
#------------------------------------------------------------------------------#
class EventTests (unittest.TestCase):
    """Event unit tests
    """
    def testSubscribe (self):
        """Test add and remove
        """
        values = []
        def handler (value):
            values.append (value)
            return True

        # create
        event = Event ()
        event (0)

        # add
        event.Subscribe (handler)
        event (1)
        self.assertEqual (values, [1])

        # remove
        self.assertTrue (event.Unsubscribe (handler))
        event (2)
        self.assertEqual (values, [1])

        # double remove
        self.assertFalse (event.Unsubscribe (handler))
        event (3)
        self.assertEqual (values, [1])

    def testAwait (self):
        """Test await
        """
        event = Event ()
        awaiter = event.Await ()
        value = []

        # not completed
        self.assertFalse (awaiter.IsCompleted ())
        awaiter.OnCompleted (lambda result, error: value.append ((result, error)))
        with self.assertRaises (ValueError):
            awaiter.GetResult ()

        # complete
        event ('done')
        self.assertTrue (awaiter.IsCompleted ())
        self.assertEqual (awaiter.GetResult (), (('done',), None))
        self.assertEqual (value, [(('done',), None)])
        del value [:]

        # completed
        awaiter.OnCompleted (lambda result, error: value.append ((result, error)))
        self.assertEqual (value, [(('done',), None)])

# vim: nu ft=python columns=120 :
