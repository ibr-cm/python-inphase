from inphase import Experiment
from inphase import decodeBinary
from inphase import decodeParameters

import time
import math
import serial
import select
import threading
import socket


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

class InphasectlMeasurementProvider(MeasurementProvider):
    def __init__(self, serial_port, count=0, target=None, baudrate=38400):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.remaining_bindec = bytes()
        self.remaining_padec = bytes()
        self.remaining = self.remaining_padec
        self.clean = bytes()
        self.measurements = list()
        self.measurements_lock = threading.Lock()
        self.running = True
        self.child_thread = threading.Thread(target=self.serial_thread)
        self.child_thread.start()
        self.parameters = dict()
        self.target = target
        self.count = count
        self.measuring = False

    def get_param(self, param, ser):
        print("Getting parameter '%s' " % param)
        self.send_cmd('get %s' % param, ser)

    def set_param(self, param, value, ser):
        print("Setting '%s' to value '%s'" % (param, value))
        self.send_cmd('set %s %s' % (param, value), ser)

    def send_cmd(self, cmd_str, ser):
        ser.write(b"inphasectl %s \n" % cmd_str.encode('utf-8'))
        ser.flush()  # it is buffering. required to get the data out *now*

    def serial_thread(self):
        # serial_for_url() allows more fancy usage of this class
        try:
            with serial.serial_for_url(self.serial_port, self.baudrate, timeout=0) as self.ser:
                self.get_param("distance_sensor0.target", self.ser)
                while self.running:
                    avail_read, avail_write, avail_error = select.select([self.ser], [], [], 1)
                    ser_data = self.ser.read(1000)
                    # print("ser_data: {}".format(ser_data))
                    measurements, self.remaining, clean = decodeBinary(self.remaining + ser_data)
                    # print("bindec -> remaining: {}".format(self.remaining))
                    print("bindec -> len measurements: {}".format(len(measurements)))
                    if clean != b'':
                        # print("bindec -> clean: {}".format(clean))
                        # print("padec -> data: {}".format(self.remaining_padec + clean))
                        decoded_parameters, self.remaining_padec, clean = decodeParameters(self.remaining_padec + clean)
                        self.parameters.update(decoded_parameters)
                        # print("padec -> parameters: {}".format(self.parameters))
                        # print("padec  -> clean: {}".format(clean))

                        if "distance_sensor0.target" not in self.parameters:
                            # print("bad! target not found")
                            self.get_param("distance_sensor0.target", self.ser)
                        elif "distance_sensor0.count" not in self.parameters:
                            # print("bad! count not found")
                            self.get_param("distance_sensor0.count", self.ser)
                        elif "distance_sensor0.start" not in self.parameters:
                            # print("bad! start not found")
                            self.get_param("distance_sensor0.start", self.ser)
                        else:
                            target = self.parameters['distance_sensor0.target']
                            # print("nice! distance_sensor0.target is {}".format(target))
                            if self.target is not None and target != self.target:
                                self.set_param("distance_sensor0.target", self.target, self.ser)

                            count = self.parameters['distance_sensor0.count']
                            print("nice! distance_sensor0.count is {}".format(count))
                            new_count = self.count - len(self.measurements)
                            if new_count == 0:
                                print("measurements done")
                                self.measuring = False

                            print("should provide {} measurements having {} remaining {}".format(self.count, len(self.measurements), new_count))
                            if self.count is not 0 and count != self.count:
                                self.set_param("distance_sensor0.count", new_count, self.ser)

                            start = self.parameters['distance_sensor0.start']
                            # print("nice! distance_sensor0.start is {}".format(start))
                            if new_count > 0 and start is not 1:
                                self.set_param("distance_sensor0.start", 1, self.ser)
                                self.measuring = True
                            elif new_count == 0:
                                print("stopping measurements")
                                self.set_param("distance_sensor0.start", 0, self.ser)

                    with self.measurements_lock:
                        self.measurements += measurements
                    self.clean += clean
        except serial.serialutil.SerialException:
            print('ERROR: serial port %s not available' % (self.serial_port))

    def getMeasurements(self):
        # while self.measuring:
            # pass
        with self.measurements_lock:
            measurements = self.measurements
            self.measurements = list()  # use a new list, to not return the last measurements again

        print("returning")
        return measurements

    def close(self):
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
