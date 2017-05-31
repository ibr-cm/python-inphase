#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataformat import Experiment, Measurement
from binarydecoder import decodeBinary

import unittest
import time
import math

class MeasurementProvider:
    pass


class BinaryFileMeasurementProvider(MeasurementProvider):

    def __init__(self, file_name, output_rate=1, loop=True):
        self.output_rate = output_rate
        self.loop = loop

        with open(file_name, 'rb') as f:
            self.measurements, self.remaining, self.clean = decodeBinary(f.read())

        self.last_timestamp = time.time()
        self.last_index = 0

    def getMeasurements(self):
        # get current time
        t = time.time()

        # time since last call to this function
        delta = t - self.last_timestamp

        # number of measurements that need to be returned (have been generated since the last call)
        measurement_count = math.floor(delta * self.output_rate)

        # get measurements from list
        to_return = list()
        if self.loop:
            for i in range(measurement_count):
                self.last_index = (self.last_index + i) % len(self.measurements)
                to_return.append(self.measurements[self.last_index])
        else:
            to_return = self.measurements[self.last_index:self.last_index+measurement_count]
            self.last_index += measurement_count

        # timestamp from this call is saved only when measurements were returned
        if measurement_count > 0:
            self.last_timestamp = t

        return to_return


class UnitTest(unittest.TestCase):

    def setUp(self):
        pass

    def test_BinaryFileMeasurementProvider(self):
        p = BinaryFileMeasurementProvider('testdata/serial_data/test_13.txt', output_rate=10, loop=True)
        self.assertEqual(len(p.getMeasurements()), 0)
        time.sleep(0.1)
        self.assertEqual(len(p.getMeasurements()), 1)
        time.sleep(0.5)
        self.assertEqual(len(p.getMeasurements()), 5)

        p = BinaryFileMeasurementProvider('testdata/serial_data/test_13.txt', output_rate=1000, loop=True)
        self.assertGreaterEqual(len(p.getMeasurements()), 0)
        time.sleep(0.1)
        self.assertGreaterEqual(len(p.getMeasurements()), 100)
        time.sleep(0.5)
        self.assertGreaterEqual(len(p.getMeasurements()), 500)

        p = BinaryFileMeasurementProvider('testdata/serial_data/test_13.txt', output_rate=10000, loop=False)
        time.sleep(0.1)
        self.assertEqual(len(p.getMeasurements()), 665)
        self.assertEqual(len(p.getMeasurements()), 0)

        p = BinaryFileMeasurementProvider('testdata/serial_data/test_13.txt', output_rate=0.1, loop=True)
        self.assertEqual(len(p.getMeasurements()), 0)
        time.sleep(2)
        self.assertEqual(len(p.getMeasurements()), 0)
        time.sleep(3)
        self.assertEqual(len(p.getMeasurements()), 0)
        time.sleep(2)
        self.assertEqual(len(p.getMeasurements()), 0)
        time.sleep(3)
        self.assertEqual(len(p.getMeasurements()), 1)


if __name__ == "__main__":
    unittest.main()
