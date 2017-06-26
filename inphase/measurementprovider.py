from inphase import Experiment
from inphase import decodeBinary
from inphase import decodeParameters
from inphase.inphasectl import inphasectl

import time
import math
import serial
import select
import threading
import socket
import logging

class MeasurementProvider:

    def close(self):
        pass


class ConstantRateMeasurementProvider(MeasurementProvider):

    def __init__(self, measurements, output_rate=1, loop=True):
        self.measurements = measurements
        self.output_rate = output_rate
        self.loop = loop

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
                self.last_index = (self.last_index + 1) % len(self.measurements)
                to_return.append(self.measurements[self.last_index])
        else:
            to_return = self.measurements[self.last_index:self.last_index+measurement_count]
            self.last_index += measurement_count

        # timestamp from this call is saved only when measurements were returned
        if measurement_count > 0:
            self.last_timestamp = t

        return to_return


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
        with serial.serial_for_url(self.serial_port, self.baudrate, timeout=0) as self.ser:
            while self.running:
                avail_read, avail_write, avail_error = select.select([self.ser], [], [], 1)
                ser_data = self.ser.read(1000)
                measurements, self.remaining, clean = decodeBinary(self.remaining + ser_data)
                with self.measurements_lock:
                    self.measurements += measurements
                self.clean += clean

    def getMeasurements(self):
        with self.measurements_lock:
            measurements = self.measurements
            self.measurements = list()  # use a new list, to not return the last measurements again
        return measurements

    def close(self):
        self.running = False

class InphasectlMeasurementProvider(MeasurementProvider):
    """ A MeasurementProvider using inphasectl to setup node and get measurements on demand."""
    def __init__(self, serial_port=None, baudrate=38400, address=None, port=50000, count=3, target=None):
        self.count = count
        self.target = target
        self.remaining = bytes()
        self.measurements = list()
        self.measurements_lock = threading.Lock()
        self.running = True
        logger = logging.getLogger('inphase.inphasectl')
        self.node = inphasectl(logger=logger)
        self.node.connect(serial_port, baudrate, address, port)
        self.child_thread = threading.Thread(target=self.measurement_thread)
        self.child_thread.start()

    def write_cfg(self, target, count):
        """ Write settings to node and read back.

        Args:
            target (int, optional): Address of node to do measurements with.
            count (int,optional): Number of measurements to do.
        
        Raises:
            ValueError: If value on node does not match setted.
        """
        if target == None:
            target = self.target

        if count == None:
            count = self.count

        settings = dict()
        settings['distance_sensor0.target'] = target
        settings['distance_sensor0.count'] = count

        for parameter_to_set in settings:
            value_to_set = settings[parameter_to_set]
            self.node.set_param(parameter_to_set, value_to_set)
            parameter_read = self.node.get_param_block(parameter_to_set)
            if parameter_read is not value_to_set:
                raise ValueError("Setting parameter failed %s", parameter_to_set)

    def process_data_stream(self, data):
        """ Process read datastream and extract measurements from binary data
        
        Args:
            data (str): datastream to process
            
        Returns:
            measurements (list): List of measurements extracted
        """

        # print("datastream: {}".format(data))
        measurements, self.remaining, clean = decodeBinary(self.remaining + data)
        # print("bindec -> remaining: {}".format(self.remaining))
        # print("bindec -> len measurements: {}".format(len(measurements)))
        # print("bindec -> clean: {}".format(clean))
        return measurements

    def measurement_thread(self):
        while self.running:
            while self.node.remaining_padec != b'':
                time.sleep(2.5)
            measurements = self.process_data_stream(self.node.clean)
            time.sleep(2.5)
            with self.measurements_lock:
                self.measurements += measurements

    def getMeasurements(self):
        self.write_cfg()
        # print("measurements start")
        # self.node.start()
        while self.node.measuring:
            # print("waiting measuring %s running %s" % (self.measuring, self.running))
            time.sleep(2.0)
        print("measurements done")
        with self.measurements_lock:
            measurements = self.measurements
            self.measurements = list()  # use a new list, to not return the last measurements again

        return measurements

    def close(self):
        print("closing")
        self.node.disconnect()
        self.running = False


class BinaryFileMeasurementProvider(ConstantRateMeasurementProvider):

    def __init__(self, file_names, output_rate=1, loop=True):
        self.measurements = list()
        self.clean = bytes()
        if not isinstance(file_names, list):
            file_names = [file_names]
        for file_name in file_names:
            with open(file_name, 'rb') as f:
                m, r, c = decodeBinary(f.read())
            self.measurements += m
            self.clean += c

        super(BinaryFileMeasurementProvider, self).__init__(self.measurements, output_rate, loop)


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


class YAMLMeasurementProvider(MeasurementProvider):

    def __init__(self, experiment_file, realtime=True, output_rate=1, loop=True):
        self.realtime = realtime
        self.measurements = Experiment(experiment_file).measurements

        # if this should not run in real time, just use the constant rate provider...
        if not self.realtime:
            self.provider = ConstantRateMeasurementProvider(self.measurements, output_rate, loop)
            self.getMeasurements = self.provider.getMeasurements
        else:
            for m in self.measurements:
                if 'timestamp' not in m:
                    raise Exception('Measurements do not contain timestamps!')
            self.loop = loop
            self.last_index = -1
            self.time_offset = time.time() - self.measurements[0]['timestamp']
            self.last_timestamp = self.measurements[0]['timestamp']

    def getMeasurements(self):
        # get current system time and convert to measurement time
        current_time = time.time()
        measurement_time = current_time - self.time_offset

        to_return = list()

        i = self.last_index
        while True:
            i += 1
            if i >= len(self.measurements):
                if not self.loop:
                    # not looping, break here
                    break
                else:
                    # start over
                    i = 0
                    self.time_offset = current_time - self.measurements[0]['timestamp']
                    measurement_time = self.measurements[0]['timestamp']
            if self.measurements[i]['timestamp'] > measurement_time:
                break

            to_return += [self.measurements[i]]
            self.last_index = i

        self.last_timestamp = measurement_time
        return to_return
