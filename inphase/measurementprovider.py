#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataformat import Experiment
from binarydecoder import decodeBinary

import unittest
import time
import math
import serial
import select
import threading
import socket


class MeasurementProvider:

    def close(self):
        pass


class SerialMeasurementProvider(MeasurementProvider):

    def __init__(self, serial_port, baudrate=38400):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.remaining = bytes()
        self.clean = bytes()
        self.measurements = list()
        self.measurements_lock = threading.Lock()
        self.running = True
        self.child_thread = threading.Thread(target=self.serial_thread)
        self.child_thread.start()

    def serial_thread(self):
        # serial_for_url() allows more fancy usage of this class
        try:
            with serial.serial_for_url(self.serial_port, self.baudrate, timeout=0) as self.ser:
                while self.running:
                    avail_read, avail_write, avail_error = select.select([self.ser], [], [], 1)
                    ser_data = self.ser.read(1000)
                    measurements, self.remaining, clean = decodeBinary(self.remaining + ser_data)
                    with self.measurements_lock:
                        self.measurements += measurements
                    self.clean += clean
        except serial.serialutil.SerialException:
            print('ERROR: serial port %s not available' % (self.serial_port))

    def getMeasurements(self):
        with self.measurements_lock:
            measurements = self.measurements
            self.measurements = list()  # use a new list, to not return the last measurements again
        return measurements

    def close(self):
        self.running = False


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


class InPhaseBridgeMeasurementProvider(MeasurementProvider):

    def __init__(self, address, port=50000):
        self.address = address
        self.port = port
        self.remaining = bytes()
        self.clean = bytes()
        self.measurements = list()
        self.measurements_lock = threading.Lock()
        self.running = True
        self.child_thread = threading.Thread(target=self.socket_thread)
        self.child_thread.start()

    def socket_thread(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.address, self.port))
        while self.running:
            avail_read, avail_write, avail_error = select.select([self.sock], [], [], 1)
            sock_data = self.sock.recv(1000)
            measurements, self.remaining, clean = decodeBinary(self.remaining + sock_data)
            with self.measurements_lock:
                self.measurements += measurements
            self.clean += clean
        self.sock.close()

    def getMeasurements(self):
        with self.measurements_lock:
            measurements = self.measurements
            self.measurements = list()  # use a new list, to not return the last measurements again
        return measurements

    def close(self):
        self.running = False


class UnitTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        self.p.close()

    @unittest.skip("test cannot work in CI")
    def test_SerialMeasurementProvider(self):
        self.p = SerialMeasurementProvider('/dev/ttyUSB0')
        time.sleep(2)  # wait for some measurements to arrive
        self.assertGreaterEqual(len(self.p.getMeasurements()), 1)

    def test_BinaryFileMeasurementProvider1(self):
        self.p = BinaryFileMeasurementProvider('testdata/serial_data/test_13.txt', output_rate=10, loop=True)
        self.assertEqual(len(self.p.getMeasurements()), 0)
        time.sleep(0.1)
        self.assertEqual(len(self.p.getMeasurements()), 1)
        time.sleep(0.5)
        self.assertEqual(len(self.p.getMeasurements()), 5)

    def test_BinaryFileMeasurementProvider2(self):
        self.p = BinaryFileMeasurementProvider('testdata/serial_data/test_13.txt', output_rate=1000, loop=True)
        self.assertGreaterEqual(len(self.p.getMeasurements()), 0)
        time.sleep(0.1)
        self.assertGreaterEqual(len(self.p.getMeasurements()), 100)
        time.sleep(0.5)
        self.assertGreaterEqual(len(self.p.getMeasurements()), 500)

    def test_BinaryFileMeasurementProvider3(self):
        self.p = BinaryFileMeasurementProvider('testdata/serial_data/test_13.txt', output_rate=10000, loop=False)
        time.sleep(0.1)
        self.assertEqual(len(self.p.getMeasurements()), 665)
        self.assertEqual(len(self.p.getMeasurements()), 0)

    def test_BinaryFileMeasurementProvider4(self):
        self.p = BinaryFileMeasurementProvider('testdata/serial_data/test_13.txt', output_rate=0.1, loop=True)
        self.assertEqual(len(self.p.getMeasurements()), 0)
        time.sleep(2)
        self.assertEqual(len(self.p.getMeasurements()), 0)
        time.sleep(3)
        self.assertEqual(len(self.p.getMeasurements()), 0)
        time.sleep(2)
        self.assertEqual(len(self.p.getMeasurements()), 0)
        time.sleep(3)
        self.assertEqual(len(self.p.getMeasurements()), 1)

    @unittest.skip("test cannot work in CI")
    def test_InPhaseBridgeMeasurementProvider(self):
        self.p = InPhaseBridgeMeasurementProvider('localhost')
        time.sleep(2)
        self.assertGreaterEqual(len(self.p.getMeasurements()), 1)


if __name__ == "__main__":
    unittest.main()
