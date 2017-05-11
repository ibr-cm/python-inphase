#!/usr/bin/python3
import socket
import sys
import threading
import time
import glob
import subprocess

import serial

import logging
logging.basicConfig(level=logging.INFO)

ser_lock = threading.Lock()  # lock for serial object between threads
ser_conn = None              # serial connection object


# from: http://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread-in-python
class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class SerialThread(StoppableThread):

    def __init__(self, timeout=0.1):
        super(SerialThread, self).__init__()
        self.timeout = timeout
        self.current_device = None
        global ser_conn
        ser_lock.acquire()
        ser_conn = serial.Serial(None, 38400, timeout=self.timeout)
        ser_lock.release()

    def getDevice(self):
        usb_ports = glob.glob('/dev/ttyUSB*')
        normal_ports = glob.glob('/dev/ttyS*')

        # use USB serial device if available
        if len(usb_ports) > 0:
            return usb_ports[0]
        elif len(normal_ports) > 0:
            return normal_ports[0]

        return None

    def run(self):
        global ser_conn, ser_lock
        while not self.stopped():
            best_device = self.getDevice()
            if best_device != self.current_device:
                with ser_lock:
                    if ser_conn.isOpen():
                        logging.warn('Closing serial port %s', self.current_device)
                        ser_conn.close()
                    if best_device is None:
                        logging.warn('No serial port found!')
                    else:
                        time.sleep(1)  # give udev a bit of time here to trigger
                        ser_conn.port = best_device
                        try:
                            ser_conn.open()
                            logging.info('Connected to serial port %s', best_device)
                        except serial.serialutil.SerialException:
                            # sometimes the device becomes unavailable between getDevice() and open()
                            # just try again next time
                            logging.warn('Could not connect to serial port %s', best_device)
                    self.current_device = best_device
            time.sleep(1)  # wait a bit to reduce CPU load


class TCPThread(StoppableThread):

    def __init__(self, host, port):
        super(TCPThread, self).__init__()
        self.host = host
        self.port = port
        self.conn = None
        self.s = None

    def run(self):
        while not self.stopped():
            for res in socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC,
                                          socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
                af, socktype, proto, canonname, sa = res
                try:
                    self.s = socket.socket(af, socktype, proto)
                except OSError as msg:
                    logging.error('OSError: %s', msg)
                    self.s = None
                    continue
                try:
                    self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)     # do not wait for TCP TIMED_WAIT
                    self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)     # do not use nagle and send directly
                    self.s.bind(sa)
                    self.s.listen(1)
                    logging.info('Listening on %s:%s', self.host, self.port)
                except OSError as msg:
                    logging.error('OSError: %s', msg)
                    self.s.close()
                    self.s = None
                    continue
                break
            if self.s is None:
                logging.error('could not open socket')
                sys.exit(1)
            self.s.setblocking(False)
            while True:
                if self.stopped():
                    return 0
                # wait for connection
                try:
                    self.conn, addr = self.s.accept()
                except BlockingIOError:
                    continue
                break  # break if we have a connection
            with self.conn:
                self.conn.setblocking(False)                                             # non-blocking receive
                logging.info('Connected: %s', addr)
                self.loop()
                logging.info('Disconnected: %s', addr)

    def loop(self):
        while not self.stopped():
            time.sleep(0.1)


class NetworkingThread(TCPThread):

    def __init__(self, host=None, port=50000):
        super(NetworkingThread, self).__init__(host, port)

    def loop(self):
        while not self.stopped():
            time.sleep(0.1)
            with ser_lock:
                try:
                    data = self.conn.recv(1024)
                    if data:
                        logging.debug('write to serial: %s', data)
                        try:
                            ser_conn.write(data)
                        except serial.serialutil.SerialException as msg:
                            logging.error('SerialException: %s', msg)
                    data = ser_conn.read(1024)
                    if data:
                        logging.debug('read from serial: %s', data)
                        try:
                            self.conn.send(data)
                        except BrokenPipeError:
                            break
                except BlockingIOError as msg:
                    pass


class ControlThread(TCPThread):

    def __init__(self, host=None, port=50001, reset_pin=None):
        super(ControlThread, self).__init__(host, port)
        self.reset_pin = reset_pin

    def loop(self):
        data = bytearray()  # byte buffer that behaves like a file
        while not self.stopped():
            time.sleep(0.1)
            try:
                data += self.conn.recv(1024)
            except BlockingIOError:
                pass
            # process all lines found
            while b'\n' in data:
                (line, data) = data.split(b'\n', 1)
                line = line.rstrip()
                if line == b'RESET':
                    if 'USB' in ser_conn.name:
                        # TODO: reset via inga_tool if device is connected via USB
                        self.conn.send(b'501 NOT IMPLEMENTED (usb reset not supported)\n')
                        continue
                    # when it is not a USB device, reset via gpio binary
                    try:
                        subprocess.run(['gpio', 'mode', str(self.reset_pin), 'out'])
                        subprocess.run(['gpio', 'write', str(self.reset_pin), '0'])
                        subprocess.run(['gpio', 'mode', str(self.reset_pin), 'in'])
                    except FileNotFoundError:
                        # this can fail on machines that do not have the gpio binary
                        self.conn.send(b'501 NOT IMPLEMENTED (gpio binary missing)\n')
                elif line == b'STATUS':
                    self.conn.send(b'200 OK\n')
                    with ser_lock:
                        ser_status = b'True' if ser_conn.isOpen() else b'False'
                        self.conn.send(b'Device: ' + bytes(ser_conn.name, encoding='utf-8') + b'\n')
                        self.conn.send(b'Connected: ' + ser_status + b'\n')
                else:
                    self.conn.send(b'400 BAD REQUEST\n')

if __name__ == "__main__":
    import signal

    def signal_handler(signal, frame):
        logging.info('Exiting...')
        serial_thread.stop()
        networking_thread.stop()
        control_thread.stop()

    signal.signal(signal.SIGINT, signal_handler)

    serial_thread = SerialThread()
    networking_thread = NetworkingThread()
    control_thread = ControlThread(reset_pin=7)

    serial_thread.start()
    networking_thread.start()
    control_thread.start()

    serial_thread.join()
    networking_thread.join()
    control_thread.join()

    logging.info('Goodbye!')
