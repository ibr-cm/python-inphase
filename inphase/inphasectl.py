import select
import serial
import socket
import threading
import time
import logging
import queue

from inphase.parameterdecoder import decodeParameters

class inphasectl():
    """Python counterpart of inphasectl which is running as contiki-shell.
    This class uses logging for output.

    Args:
        logger (:obj:`logging`, optional): logger to use
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.measuring = False
        self.active = False
        self.clean = bytearray()
        self.received_data = bytearray()
        self.received_data_lock = threading.Lock()
        self.write_data_lock = threading.Lock()
        self.read_parameters = dict()
        self.remaining_padec = bytearray()
        self.single_query = False
        self.data_queue = queue.Queue() 
        self.logger.info("init done")

    def connect(self, serial_port=None, baudrate=38400, address=None, port=50000):
        """
        Try to connect to device. This could be done either via serial_port
        or socket connection. 
        
        Args:
            serial_port (str, optional): Device path to use, e.g. `/dev/ttyUSB0`
            baudrate (int, optional): Baudrate to use
            address (str, optional): Use this address for socket mode
            port (int, optional): Port to use

        Note: 
            At least one arguments must be given of `serial_port` or `address`
        """

        self.serial_port = serial_port
        self.address = address
        if serial_port is not None:
            self.baudrate = baudrate
            self.child_thread = threading.Thread(target=self.serial_thread)
            self.logger.info("serial_port mode port %s baudrate %d", serial_port, baudrate)
        elif address is not None:
            self.port = port
            self.child_thread = threading.Thread(target=self.socket_thread)
            self.logger.info("socket mode address", address, "port", port)
        else:
            raise Exception("Neither serial_port nor address set")
        try:
            self.ser = serial.serial_for_url(self.serial_port, self.baudrate, timeout=0)
        except serial.serialutil.SerialException:
            self.logger.error('ERROR: serial port %s not available' % (self.serial_port))
            self.running = False

        self.child_thread.start()


    def disconnect(self):
        """Disconnect from device."""
        self.running = False
        self.child_thread.join()

    def get_param(self, param):
        """Get parameter from device. This blocks until the request
        parameter is received.

        Note:
            This aborts after approx. 10 sec

        Args:
            param (str): Name of parameter to get
        """
        self.read_parameters[param] = None
        self.logger.info("deleted saved parameter")
        self.__get_param(param)
        counter = 0
        while self.read_parameters[param] == None:
            if counter == 10:
                raise Exception("Device does not answer")
            counter += 1
            time.sleep(1)

        return self.read_parameters[param]

    def __get_param(self, param):
        self.logger.info("Getting parameter '%s' " % param)
        self.send_cmd('get %s' % param)

    def set_param(self, param, value):
        self.read_parameters[param] = None
        self.logger.info("deleted saved parameter")
        self.logger.info("Setting '%s' to value '%s'" % (param, value))
        self.send_cmd('set %s %s' % (param, value))
        counter = 0
        while self.read_parameters[param] == None:
            if counter == 10:
                raise Exception("Device does not answer")
            counter += 1
            time.sleep(1)

        return self.read_parameters[param] == value

    def start(self):
        self.set_param('distance_sensor0.start', 1)
        self.single_query = False
        self.measuring = True

    def list_parameters(self, device = b''):
        if device != b'':
            self.logger.info("listing parameters of device", device)
            self.send_cmd('list_parameters %s' % device)
        else:
            self.logger.info("listing all parameters")
            self.send_cmd('list_parameters')

    def list_devices(self):
        self.logger.info("listing devices")
        self.send_cmd("list-devices")

    def send_cmd(self, cmd_str):
        with self.write_data_lock:
            if self.serial_port is not None:
                self.ser.write(b"inphasectl %s \n" % cmd_str.encode('utf-8'))
                self.ser.flush()  # it is buffering. required to get the data out *now*
                self.logger.info("request send")
            elif self.address is not None:
                self.sock.send(b"inphasectl %s \n" % cmd_str.encode('utf-8'))

    def socket_thread(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.sock:
            self.running = True
            self.sock.connect((self.address, self.port))
            while self.running:
                avail_read, avail_write, avail_error = select.select([self.sock], [], [], 1)
                with self.received_data_lock:
                    self.received_data = self.sock.recv(1000)
            # TODO: maybe delete read_parameters here, becaue we will be out of sync
            self.logger.info("socket_thread stopped")

    def serial_thread(self):
        # serial_for_url() allows more fancy usage of this class
        self.running = True
        self.logger.info("serial_thread started")
        while self.running:
            avail_read, avail_write, avail_error = select.select([self.ser], [], [], 1)
            self.received_data = self.ser.read(1000)

            decoded_parameters, self.remaining_padec, clean = decodeParameters(self.remaining_padec + self.received_data)
            self.read_parameters.update(decoded_parameters)
            self.logger.debug("clean %s" % clean)
            if clean != b'':
                self.data_queue.put(clean)

            # if not self.active:
                # if 'distance_sensor0.start' not in self.read_parameters:
                    # self.get_param('distance_sensor0.start')
            # elif self.read_parameters['distance_sensor0.start'] ==  None:
                # self.logger.debug("waiting for start state")
            # elif self.read_parameters['distance_sensor0.start'] ==  0:
                # self.logger.debug("inphasectl not active")
                # if self.active:
                    # self.measuring = False
                    # self.logger.info("measurements done")
                # elif self.measuring:
                    # self.set_param('distance_sensor0.start', 1)
            # elif self.read_parameters['distance_sensor0.start'] ==  1:
                # self.logger.debug("inphasectl active")
                # self.active = True
        # TODO: maybe delete read_parameters here, becaue we will be out of sync
        self.logger.info("serial_thread stopped")
        self.ser.close()

