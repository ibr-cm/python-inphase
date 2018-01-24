#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import unittest
import logging
import threading

from inphase.inphasectl import inphasectl
try:
    from tests import inphasectl_mockup
except ImportError:
    import inphasectl_mockup


class TestInphasectlNode(unittest.TestCase):
    '''
    With this testcase the inphasectl implementation can be tested against an
    inphasectl mockup or the inphasectl implementation on node against a real device
    '''
    logger = logging.getLogger('inphase.test.inphasectl')
    node = inphasectl()

    DEVICE_URL = inphasectl_mockup.URL
    BAUDRATE = 38400

    def setUp(self):
        '''
        Connect to device. In default the inphasectl mockup is stated in a thread
        and a connection to it will be established.
        '''
        if self.DEVICE_URL == inphasectl_mockup.URL:
            self.logger.info("Starting own inphasectl mockup")
            self.inphasectl_mockup_thread = threading.Thread(target=inphasectl_mockup.main)
            self.inphasectl_mockup_thread.start()
            time.sleep(1)  # wait for thread to be ready

        self.assertFalse(self.node.running)
        self.node.connect(serial_port=self.DEVICE_URL, baudrate=self.BAUDRATE)

    def tearDown(self):
        '''
        Disconnect from device.
        '''
        self.node.disconnect()
        self.assertFalse(self.node.running)

    def test_connected(self):
        '''
        Test whether connecting in setup was successful.
        '''
        self.logger.info(">> test_connect_serial")
        counter = 0
        while not self.node.running:
            counter += 1
            time.sleep(0.5)
            if counter == 5:
                break
        self.assertTrue(self.node.running)

    def test_set_param(self):
        '''
        Test whether setting parameters generally works.

        Note:
            Only setting 'distance_sensor0.target' to '0x1337' is tested.
        '''
        self.logger.info(">> test_set_param")
        self.assertTrue(self.node.running)
        self.assertTrue(self.node.set_param('distance_sensor0.target', 0x1337))

    def test_get_param(self):
        '''
        Test whether getting parameters generally works.

        Note:
            Only getting 'distance_sensor0.target' is tested.
        '''
        self.logger.info(">> test_get_param")
        self.assertTrue(self.node.running)
        param = self.node.get_param('distance_sensor0.target')
        self.assertNotEqual(param, None)

    def test_get_version(self):
        '''
        Test whether getting version works.
        '''
        self.logger.info(">> test_get_version")
        self.assertTrue(self.node.running)
        param = self.node.get_param('default.version')
        self.assertNotEqual(param, None)
        self.assertTrue(param.startswith("inphasectl-"))

    @unittest.skip('Can not be tested as there is no Exception thrown')
    def test_get_unknown_param(self):
        '''
        Test whether getting an unknown parameter reports an Exception.

        Note:
            Testing this is currently no possible.

        TODO:
            Add necessary implementation to inphasectl
        '''
        self.logger.info(">> test_get_unknown_param")
        self.assertTrue(self.node.running)
        param = self.node.get_param('distance_sensor0.unknown')
        # TODO: if there is an error an exception should be thrown
        # self.assertRaises(Exception, inphase.parameterdecoder)
        self.assertEqual(param, None)

    def test_node_setup(self):
        '''
        Test setting parameters and reading after works.

        This is done for every parameter individually.
        '''
        self.logger.info(">> test_node_setup")
        self.assertTrue(self.node.running)
        settings = dict()
        settings['distance_sensor0.target'] = 0x1234
        settings['distance_sensor0.count'] = 5
        for parameter in settings:
            self.assertTrue(self.node.running)
            self.logger.debug("settings update with %s", parameter)
            self.node.set_param(parameter, settings[parameter])
            param = self.node.get_param(parameter)
            self.assertEqual(settings[parameter], param)

    def test_node_setup_fast(self):
        '''
        Test setting parameters and reading after works.

        At first all parameters are set. After that they are got.
        '''
        self.logger.info(">> test_node_setup_fast")
        self.assertTrue(self.node.running)
        settings = dict()
        settings['distance_sensor0.target'] = 0x1234
        settings['distance_sensor0.count'] = 5
        for parameter in settings:
            self.assertTrue(self.node.running)
            self.logger.debug("settings update with %s", parameter)
            self.node.set_param(parameter, settings[parameter])

        for parameter in settings:
            self.logger.debug("checking settings update with %s", parameter)
            param = self.node.get_param(parameter)
            self.assertEqual(settings[parameter], param)

    def test_start(self):
        '''
        Test whether a measurement will be done after start and return
        data for further processing, e.g. decoding binary data to
        measurements
        '''
        self.logger.info(">> test_start")
        self.assertTrue(self.node.running)
        self.node.start()
        data_to_process = self.node.data_queue.get(timeout=0.5)
        self.assertGreater(len(data_to_process), 0)

    def test_list_parameters(self):
        '''
        Test whether the `list-parameters` command returns data.

        Note:
            There is no check done whether the returned data are correct.
        '''
        self.logger.info(">> test_list_parameters")
        self.node.list_parameters()
        data_to_process = self.node.data_queue.get(timeout=0.5)
        self.assertGreater(len(data_to_process), 0)

    def test_list_devices(self):
        '''
        Test whether the `list-devices` command returns data.

        Note:
            There is no check done whether the returned data are correct.
        '''
        self.logger.info(">> test_list_devices")
        self.node.list_devices()
        data_to_process = self.node.data_queue.get(timeout=0.5)
        self.assertGreater(len(data_to_process), 0)


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Unittest of inphasectl python counterpart.')
    parser.add_argument('-d', '--device', type=str, default='socket://localhost:50005',
                        help='serial device to connect or url to device')
    parser.add_argument('-b', '--baudrate', type=int, default=38400,
                        help='baudrate to use when connecting to serial device')
    parser.add_argument('-l', '--loglevel', type=str, default='ERROR',
                        help='level of debug output on console')
    parser.add_argument('-L', '--loglevel_file', type=str, default='DEBUG',
                        help='level of debug output to file')
    parser.add_argument('-f', '--logfile', type=str, help='filename of logfile')
    args = parser.parse_args()
    del sys.argv[1:]

    # create logger
    logger = logging.getLogger()
    logger.setLevel(args.loglevel)

    # create console handler and set level to debug
    CON_HANDLER = logging.StreamHandler()
    CON_HANDLER.setLevel(args.loglevel)
    # TODO add filelogger if no console logging is wanted
    if args.logfile:
        print("Currently no support for logfiles ignoring file", args.logfile)

    # create formatter
    # TODO: use CONSTANT from inphase module
    formatter = logging.Formatter('%(name)s/%(funcName)s (%(threadName)s) - %(levelname)s - %(message)s')

    # add formatter to CON_HANDLER
    CON_HANDLER.setFormatter(formatter)

    # add CON_HANDLER to logger
    logger.addHandler(CON_HANDLER)

    logger.info("Running as program. Starting unittests")
    TestInphasectlNode.DEVICE_URL = args.device
    TestInphasectlNode.BAUDRATE = args.baudrate
    unittest.main()
