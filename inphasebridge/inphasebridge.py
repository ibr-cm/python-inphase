#!/usr/bin/python3
import socket
import sys
import threading
import time
import glob

import serial
import serial.tools.list_ports


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
                            continue
                    self.current_device = best_device
            time.sleep(1)  # wait a bit to reduce CPU load


class NetworkingThread(StoppableThread):

    def __init__(self, host=None, port=50000):
        super(NetworkingThread, self).__init__()
        self.host = host
        self.port = port

    def run(self):
        while not self.stopped():
            for res in socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC,
                                          socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
                af, socktype, proto, canonname, sa = res
                try:
                    s = socket.socket(af, socktype, proto)
                except OSError as msg:
                    logging.error('OSError: %s', msg)
                    s = None
                    continue
                try:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)     # do not wait for TCP TIMED_WAIT
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)     # do not use nagle and send directly
                    s.bind(sa)
                    s.listen(1)
                    logging.info('Listening on %s:%s', self.host, self.port)
                except OSError as msg:
                    logging.error('OSError: %s', msg)
                    s.close()
                    s = None
                    continue
                break
            if s is None:
                logging.error('could not open socket')
                sys.exit(1)
            conn, addr = s.accept()
            conn.setblocking(False)                                             # non-blocking receive
            with conn:
                logging.info('Connected: %s', addr)
                while not self.stopped():
                    time.sleep(0.1)
                    with ser_lock:
                        try:
                            data = conn.recv(1024)
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
                                    conn.send(data)
                                except BrokenPipeError:
                                    break
                        except BlockingIOError as msg:
                            pass
                logging.info('Disconnected: %s', addr)

if __name__ == "__main__":
    import signal

    def signal_handler(signal, frame):
        logging.info('Exiting...')
        serial_thread.stop()
        networking_thread.stop()

    signal.signal(signal.SIGINT, signal_handler)
    serial_thread = SerialThread()
    networking_thread = NetworkingThread()
    serial_thread.start()
    networking_thread.start()
    serial_thread.join()
    networking_thread.join()
    logging.info('Goodbye!')
