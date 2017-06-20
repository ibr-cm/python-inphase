#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import inphase

import unittest
import os
THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class UnitTest(unittest.TestCase):

    def setUp(self):
        with open(os.path.join(THIS_DIR, 'testdata/serial_data/inphasectl_single_shot.txt'), 'rb') as f:
            self.serial_dump = f.read()
        self.serial_data = b'test_key: 1234\r\nContiki is nice\r\nincompl'

    def test_parsing_complete(self):
        remaining_data = bytes()
        parameters = dict()
        remaining_data = self.serial_data
        p, remaining_data, c = inphase.decodeParameters(remaining_data)
        parameters.update(p)

        self.assertEqual(len(parameters), 1)
        self.assertDictEqual(parameters, {'test_key': 1234})
        self.assertEqual(c, b'Contiki is nice\r\n')
        self.assertEqual(remaining_data, b'incompl')

    def test_parsing_pieces(self):
        # split serial data into pieces of 10 bytes
        data_pieces = [self.serial_data[i:i+10] for i in range(0, len(self.serial_data), 10)]
        remaining_data = bytes()
        parameters = dict()
        for d in data_pieces:
            remaining_data += d
            remaining_data_before = remaining_data
            p, remaining_data, c = inphase.decodeParameters(remaining_data)
            parameters.update(p)
            if not p:
                self.assertEqual(c+remaining_data, remaining_data_before)

        self.assertEqual(len(parameters), 1)
        self.assertDictEqual(parameters, {'test_key': 1234})

    def test_parsing_false_positive(self):
        remaining_data = bytes()
        parameters = dict()
        test_data_unmatch = b'.distance_status: DISTANCE_RUNNING\r\n'
        test_data_unmatch += b'..distance_status: DISTANCE_RUNNING\r\n'
        test_data_unmatch += b'sensor..param1: value1\r\n'
        test_data_unmatch += b'sensor..param1.subparam1: subvalue1\r\n'
        test_data_unmatch += b'sensor..param1.subparam1: subvalue1\r\n'
        remaining_data = test_data_unmatch
        parameters_found, remaining_data, clean = inphase.decodeParameters(remaining_data)
        parameters.update(parameters_found)
        self.assertEqual(len(parameters), 0)
        self.assertEqual(clean, test_data_unmatch)
        self.assertEqual(remaining_data, b'')

        test_data_match = b'param1: value1\r\n'
        test_data_match += b'sensor.param1: value1\r\n'
        test_data_match += b'sensor.param1.subparam1: subvalue1\r\n'
        test_data_match += b'sensor.param1.subparam1.sub1: subsubvalue1\r\n'

        remaining_data = test_data_match
        parameters_found, remaining_data, clean = inphase.decodeParameters(remaining_data)
        parameters.update(parameters_found)
        self.assertEqual(len(parameters), 4)
        self.assertEqual(clean, b'')
        self.assertEqual(remaining_data, b'')


    def test_parsing_dump(self):
        # split serial data into pieces of 10 bytes
        data_pieces = [self.serial_dump[i:i+10] for i in range(0, len(self.serial_dump), 10)]
        remaining_data = bytes()
        parameters = dict()
        for d in data_pieces:
            remaining_data += d
            remaining_data_before = remaining_data
            p, remaining_data, c = inphase.decodeParameters(remaining_data)
            parameters.update(p)
            if not p:
                self.assertEqual(c+remaining_data, remaining_data_before)
        self.assertEqual(len(parameters), 1)
        self.assertIn('distance_sensor0.start', parameters)
        self.assertEqual(parameters['distance_sensor0.start'], 1)

if __name__ == "__main__":
    unittest.main()
