#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from inphase import Experiment
from inphase.measurementprovider import *
from . import inphasectl_mockup

import unittest
import time
import socket
import os
THIS_DIR = os.path.dirname(os.path.abspath(__file__))

import logging
import sys

logger = logging.getLogger()
logger.level = logging.ERROR
formatter = logging.Formatter('%(name)s/%(funcName)s (%(threadName)s) - %(levelname)s - %(message)s')
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

logging.getLogger('inphase.parameterdecoder').setLevel(logging.ERROR)
logging.getLogger('inphase.inphasectl').setLevel(logging.ERROR)
logging.getLogger('tests.inphasectl_mockup').setLevel(logging.ERROR)
logging.getLogger('inphase.measurementprovider').setLevel(logging.ERROR)

class UnitTest(unittest.TestCase):

    def setUp(self):
        self.measurements = Experiment(os.path.join(THIS_DIR, 'testdata/measurement_data/timestamped.yml')).measurements

    def tearDown(self):
        if hasattr(self, 'p'):
            self.p.close()

    def checkTimestamps(self, measurements):
        timestamps = list()
        for m in measurements:
            timestamps.append(m['timestamp'])
        last_t = timestamps[0]
        for t in timestamps[1:]:
            self.assertGreater(t, last_t)
            last_t = t

    def test_SerialMeasurementProvider(self):
        # start a TCP server that reads from a file
        serial_sock = socket.socket()
        serial_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serial_sock.bind(('localhost', 50000))
        serial_sock.listen(1)
        serial_sock.setblocking(False)

        self.p = SerialMeasurementProvider('socket://localhost:50000')

        time.sleep(1)  # wait for SerialMeasurementProvider to connect

        # accept connection
        conn, addr = serial_sock.accept()

        with open(os.path.join(THIS_DIR, 'testdata/serial_data/test_13.txt'), 'rb') as f:
            conn.send(f.read())

        time.sleep(1)  # wait for some measurements to arrive
        measurements = self.p.getMeasurements()
        self.checkTimestamps(measurements)
        self.assertGreaterEqual(len(measurements), 1)

        conn.close()
        serial_sock.close()

    def test_InphasectlMeasurementProvider(self):
        thread = threading.Thread(target=inphasectl_mockup.main)
        thread.start()
        time.sleep(1)  # wait for thread to be ready
        self.p = InphasectlMeasurementProvider('socket://localhost:50005', count=4, target=0xdb98)
        time.sleep(1)  # wait for some measurements to arrive
        measurements = self.p.getMeasurements()
        self.assertEqual(len(measurements), 4)

    @unittest.skip("Test can't be run on CI")
    def test_InphasectlMeasurementProviderWithDevice(self):
        self.p = InphasectlMeasurementProvider('/dev/inga/node-A501I3NS', count=4, target=0xdb98)
        time.sleep(1)  # wait for some measurements to arrive
        measurements = self.p.getMeasurements()
        self.assertEqual(len(measurements), 4)

    def test_BinaryFileMeasurementProvider(self):
        self.p = BinaryFileMeasurementProvider(os.path.join(THIS_DIR, 'testdata/serial_data/test_13.txt'), output_rate=10000, loop=False)
        time.sleep(0.1)
        self.assertEqual(len(self.p.getMeasurements()), 665)
        self.assertEqual(len(self.p.getMeasurements()), 0)

    def test_BinaryFileMeasurementProviderMultiple(self):
        self.p = BinaryFileMeasurementProvider([os.path.join(THIS_DIR, 'testdata/serial_data/test_13.txt'), os.path.join(THIS_DIR, 'testdata/serial_data/test_13.txt')], output_rate=20000, loop=False)
        time.sleep(0.1)
        self.assertEqual(len(self.p.getMeasurements()), 665*2)
        self.assertEqual(len(self.p.getMeasurements()), 0)

    def test_ConstantRateMeasurementProvider1(self):
        self.p = ConstantRateMeasurementProvider(self.measurements, output_rate=10, loop=True)
        self.assertEqual(len(self.p.getMeasurements()), 0)
        time.sleep(0.1)
        self.assertEqual(len(self.p.getMeasurements()), 1)
        time.sleep(0.5)
        self.assertEqual(len(self.p.getMeasurements()), 5)

    def test_ConstantRateMeasurementProvider2(self):
        self.p = ConstantRateMeasurementProvider(self.measurements, output_rate=1000, loop=True)
        self.assertGreaterEqual(len(self.p.getMeasurements()), 0)
        time.sleep(0.1)
        self.assertGreaterEqual(len(self.p.getMeasurements()), 100)
        time.sleep(0.5)
        self.assertGreaterEqual(len(self.p.getMeasurements()), 500)

    def test_ConstantRateMeasurementProvider3(self):
        self.p = ConstantRateMeasurementProvider(self.measurements, output_rate=10000, loop=False)
        time.sleep(0.1)
        self.assertEqual(len(self.p.getMeasurements()), 7)
        self.assertEqual(len(self.p.getMeasurements()), 0)

    def test_ConstantRateMeasurementProvider4(self):
        self.p = ConstantRateMeasurementProvider(self.measurements, output_rate=0.1, loop=True)
        self.assertEqual(len(self.p.getMeasurements()), 0)
        time.sleep(2)
        self.assertEqual(len(self.p.getMeasurements()), 0)
        time.sleep(3)
        self.assertEqual(len(self.p.getMeasurements()), 0)
        time.sleep(2)
        self.assertEqual(len(self.p.getMeasurements()), 0)
        time.sleep(3)
        self.assertEqual(len(self.p.getMeasurements()), 1)

    def test_InPhaseBridgeMeasurementProvider(self):
        # start a TCP server that reads from a file
        serial_sock = socket.socket()
        serial_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serial_sock.bind(('localhost', 50000))
        serial_sock.listen(1)
        serial_sock.setblocking(False)

        self.p = InPhaseBridgeMeasurementProvider('localhost')

        time.sleep(1)  # wait for SerialMeasurementProvider to connect

        # accept connection
        conn, addr = serial_sock.accept()

        with open(os.path.join(THIS_DIR, 'testdata/serial_data/test_13.txt'), 'rb') as f:
            conn.send(f.read())

        time.sleep(1)  # wait for some measurements to arrive
        measurements = self.p.getMeasurements()
        self.checkTimestamps(measurements)
        self.assertGreaterEqual(len(measurements), 1)

        conn.close()
        serial_sock.close()

    def test_YAMLMeasurementProviderConstantRate(self):
        self.p = YAMLMeasurementProvider(os.path.join(THIS_DIR, 'testdata/measurement_data/timestamped.yml'), realtime=False, output_rate=10000, loop=False)
        time.sleep(0.1)
        self.assertEqual(len(self.p.getMeasurements()), 7)
        self.assertEqual(len(self.p.getMeasurements()), 0)

    def test_YAMLMeasurementProviderRealtimeLoop(self):
        self.p = YAMLMeasurementProvider(os.path.join(THIS_DIR, 'testdata/measurement_data/timestamped.yml'), realtime=True, loop=True)
        self.assertEqual(len(self.p.getMeasurements()), 1)
        time.sleep(1)
        self.assertEqual(len(self.p.getMeasurements()), 3)
        time.sleep(0.1)
        self.assertEqual(len(self.p.getMeasurements()), 0)
        time.sleep(0.5)
        self.assertEqual(len(self.p.getMeasurements()), 2)
        time.sleep(1)
        self.assertEqual(len(self.p.getMeasurements()), 2)
        time.sleep(1)
        self.assertEqual(len(self.p.getMeasurements()), 3)

    def test_YAMLMeasurementProviderRealtime(self):
        self.p = YAMLMeasurementProvider(os.path.join(THIS_DIR, 'testdata/measurement_data/timestamped.yml'), realtime=True, loop=False)
        self.assertEqual(len(self.p.getMeasurements()), 1)
        time.sleep(1)
        self.assertEqual(len(self.p.getMeasurements()), 3)
        time.sleep(0.1)
        self.assertEqual(len(self.p.getMeasurements()), 0)
        time.sleep(0.5)
        self.assertEqual(len(self.p.getMeasurements()), 2)
        time.sleep(1)
        self.assertEqual(len(self.p.getMeasurements()), 1)
        time.sleep(1)
        self.assertEqual(len(self.p.getMeasurements()), 0)

    def test_YAMLMeasurementProviderRealtimeFull(self):
        self.p = YAMLMeasurementProvider(os.path.join(THIS_DIR, 'testdata/measurement_data/timestamped.yml'), realtime=True, loop=False)
        time.sleep(2)
        self.assertEqual(len(self.p.getMeasurements()), 7)

    def test_YAMLMeasurementProviderException(self):
        with self.assertRaises(Exception):
            self.p = YAMLMeasurementProvider(os.path.join(THIS_DIR, 'testdata/measurement_data/experiment_no_timestamp.yml'), realtime=True, loop=False)

    def test_ConstantRateMeasurementProviderNotSame(self):
        self.p = ConstantRateMeasurementProvider(self.measurements, output_rate=1, loop=True)
        i = 0
        m_list = list()
        while i < 30:
            time.sleep(0.1)
            measurements = self.p.getMeasurements()
            if measurements:
                for m in measurements:
                    m_list.append(m)
            i += 1
        for i in range(len(m_list)-2):
            self.assertNotEqual(m_list[i]['timestamp'], m_list[i+1]['timestamp'], 'timestamps should not be equal!')


if __name__ == "__main__":
    unittest.main()
