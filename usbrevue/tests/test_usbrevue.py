#!/usr/bin/env python

import os
import os.path
import struct
import sys
import unittest
from functools import partial

import pcapy

from tutil import *
from usbrevue import *

class TestPacket(unittest.TestCase,TestUtil):

    def setUp(self):
        pcap = pcapy.open_offline(test_data('usb-single-packet-2.pcap'))
        self.packet = Packet(*pcap.next())

        self.set_and_test = partial(self.setattr_and_test, self.packet)

        # Long name, but not as long as without it
        self.assertRaisesWrongPacketXferType = partial(self.assertRaises,
                WrongPacketXferType, getattr, self.packet)

        # Verify that we have the right test data
        self.assertEqual(self.packet.length, 40, 'unmodified packet wrong--test bad?')
        self.assertEqual(self.packet.busnum, 7, 'unmodified packet wrong--test bad?')

    #def test_fail(self): self.fail('Fail works as expected')

    def test_urb(self):
        self.assertEqual(self.packet.urb, 0x00000000ef98ef00, 'Unmodified URB')

        self.set_and_test('urb', 0x00000000ef98ef01)
        self.set_and_test('urb', 0xffff0000ef98ef01)
        self.set_and_test('urb', 0)
        self.set_and_test('urb', 0xffffffffffffffff)

        self.assertRaises(TypeError, self.set_and_test, 'urb', -1)
        self.assertRaises(struct.error,         # Too large
                self.set_and_test,'urb', 0xffffffffffffffffff)

    def test_event_type(self):
        self.assertEqual(self.packet.event_type, 'S', 'Unmodified event_type')

        # "Normal" range of values
        self.set_and_test('event_type', 'C')    # Callback
        self.set_and_test('event_type', 'E')    # Error

        # Things that shouldn't be -- perhaps these should be errors?
        self.set_and_test('event_type', chr(0x00))
        self.set_and_test('event_type', chr(0xFF))

    def test_xfer_type(self):
        self.assertEqual(self.packet.xfer_type, 2, 'Unmodified xfer_type')
        self.set_and_test('xfer_type', 0, 'Isoc xfer type')
        self.set_and_test('xfer_type', 1, 'Interrupt xfer type')
        self.set_and_test('xfer_type', 2, 'Control xfer type')
        self.set_and_test('xfer_type', 3, 'Bulk xfer type')

    # Might be good to test all permutations
    def test_xfer_type_tests(self):
        self.failIf(self.packet.is_isochronous_xfer(), 'Not isoc xfer')
        self.failIf(self.packet.is_bulk_xfer(), 'Not bulk xfer')
        self.failUnless(self.packet.is_control_xfer(), 'Is control xfer')
        self.failIf(self.packet.is_interrupt_xfer(), 'Not interrupt xfer')

    def test_epnum(self):
        self.assertEqual(self.packet.epnum, 0x80, 'Unmodified epnum')

    def test_devnum(self):
        self.assertEqual(self.packet.devnum, 3, 'Unmodified devnum')

    def test_busnum(self):
        self.assertEqual(self.packet.busnum, 7, 'Unmodified busnum')

    def test_flag_setup(self):
        self.assertEqual(self.packet.flag_setup, '\x00', 'Unmodified flag_setup')

    def test_flag_data(self):
        self.assertEqual(self.packet.flag_data, '<', 'Unmodified flag_data')

    def test_ts_sec(self):
        self.assertEqual(self.packet.ts_sec, 1309208916, 'Unmodified ts_sec')

    def test_ts_usec(self):
        self.assertEqual(self.packet.ts_usec, 397516, 'Unmodified ts_usec')

    def test_status(self):
        self.assertEqual(self.packet.status, -115, 'Unmodified status')

    def test_length(self):
        self.assertEqual(self.packet.length, 40, 'Unmodified length')
        self.set_and_test('length', 99)

    def test_len_cap(self):
        self.assertEqual(self.packet.len_cap, 0, 'Unmodified len_cap')

    def test_setup(self):
        pass

    # Skipping tests is not supported until 2.7
    if sys.version_info[0] == 2 and sys.version_info[1] >= 7:
        @unittest.skip('Exception not yet implemented')
        def test_error_count(self):
            self.assertRaisesWrongPacketXferType('error_count')

        @unittest.skip('Exception not yet implemented')
        def test_numdesc(self):
            self.assertRaisesWrongPacketXferType('numdesc')

        @unittest.skip('Exception not yet implemented')
        def test_interval(self):
            self.assertRaisesWrongPacketXferType('interval')

        @unittest.skip('Exception not yet implemented')
        def test_start_frame(self):
            self.assertRaisesWrongPacketXferType('start_frame')

    def test_xfer_flags(self):
        self.assertEqual(self.packet.xfer_flags, 0x200, 'Unmodified xfer_flags')

    # FIXME Should this be an xfer_type = isoc only attribute also?
    def test_ndesc(self):
        self.assertEqual(self.packet.ndesc, 0, 'Unmodified ndesc')

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPacket)
    unittest.TextTestRunner(verbosity=3).run(suite)