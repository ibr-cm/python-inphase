#!/usr/bin/python3

import socket
import selectors
import glob
import serial
import subprocess

import logging
logging.basicConfig(level=logging.INFO)

sel = selectors.DefaultSelector()

IP = '0.0.0.0'
SERIAL_PORT = 50000
CONTROL_PORT = 50001

SELECTOR_TIMEOUT = 1  # timeout in seconds for selector (float allowed)

BAUDRATE = 38400
RESET_PIN = 7

serial_connections = list()  # this holds all serial connections for port multiplexing
ser_conn = serial.Serial(None, BAUDRATE, timeout=0)


def getDevice():
    usb_ports = glob.glob('/dev/ttyUSB*')
    normal_ports = glob.glob('/dev/ttyS*')

    # use USB serial device if available
    if len(usb_ports) > 0:
        return usb_ports[0]
    elif len(normal_ports) > 0:
        return normal_ports[0]

    return None


def control_socket_accept(sock, mask):
    conn, addr = sock.accept()  # Should be ready
    logging.info('accepted control connection from %s', addr)
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, control_socket_read)


def control_socket_read(conn, mask):
    data = conn.recv(1000)  # Should be ready
    if data:
        while b'\n' in data:
            (line, data) = data.split(b'\n', 1)
            line = line.rstrip()
            line = line.upper()

            if line == b'RESET':
                if 'USB' in ser_conn.name:
                    # TODO: reset via inga_tool if device is connected via USB
                    conn.sendall(b'501 NOT IMPLEMENTED (usb reset not supported)\n')
                    continue
                # when it is not a USB device, reset via gpio binary
                try:
                    subprocess.call(['gpio', 'mode', str(RESET_PIN), 'out'])
                    subprocess.call(['gpio', 'write', str(RESET_PIN), '0'])
                    subprocess.call(['gpio', 'mode', str(RESET_PIN), 'in'])
                    conn.sendall(b'200 OK\n')
                except FileNotFoundError:
                    # this can fail on machines that do not have the gpio binary
                    conn.sendall(b'501 NOT IMPLEMENTED (gpio binary missing)\n')
            elif line == b'STATUS':
                conn.sendall(b'Device: ' + bytes(ser_conn.name, encoding='ascii') + b'\n')
                ser_status = b'True' if ser_conn.isOpen() else b'False'
                conn.sendall(b'Connected: ' + ser_status + b'\n')
                conn.sendall(b'Connected clients: ' + bytes(str(len(serial_connections)), encoding='ascii') + b'\n')
                conn.sendall(b'200 OK\n')
            else:
                conn.sendall(b'400 BAD REQUEST\n')
    else:
        logging.info('closing %s', conn)
        sel.unregister(conn)
        conn.close()


def serial_socket_accept(sock, mask):
    conn, addr = sock.accept()  # Should be ready
    logging.info('accepted serial connection from %s', addr)
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, serial_socket_read)
    serial_connections.append(conn)


def serial_socket_read(conn, mask):
    data = conn.recv(1000)  # Should be ready
    if data:
        for s in serial_connections:
            if s == conn:
                continue
            s.sendall(data)
        logging.debug('write to serial: %s', data)
        try:
            ser_conn.write(data)
        except serial.serialutil.SerialException as msg:
            logging.error('SerialException: %s', msg)
    else:
        logging.info('closing %s', conn)
        sel.unregister(conn)
        serial_connections.remove(conn)
        conn.close()


def serial_read(conn, mask):
    try:
        data = conn.read(1024)
        for s in serial_connections:
            s.sendall(data)
    except serial.serialutil.SerialException:
        logging.warn('Closing serial port %s', conn.port)
        sel.unregister(conn)
        conn.close()

if __name__ == "__main__":
    running = True

    import signal

    def signal_handler(signal, frame):
        global running
        logging.info('Exiting...')
        running = False

    signal.signal(signal.SIGINT, signal_handler)

    serial_sock = socket.socket()
    serial_sock.bind((IP, SERIAL_PORT))
    serial_sock.listen(1)
    serial_sock.setblocking(False)
    sel.register(serial_sock, selectors.EVENT_READ, serial_socket_accept)
    logging.info('listening on %s:%s for serial connections', IP, SERIAL_PORT)
    serial_conn = None

    control_sock = socket.socket()
    control_sock.bind((IP, CONTROL_PORT))
    control_sock.listen(1)
    control_sock.setblocking(False)
    sel.register(control_sock, selectors.EVENT_READ, control_socket_accept)
    logging.info('listening on %s:%s for control connections', IP, CONTROL_PORT)

    current_device = None

    while running:
        best_device = getDevice()

        if best_device != current_device:
            if ser_conn.isOpen():
                logging.warn('Closing serial port %s', current_device)
                sel.unregister(ser_conn)
                ser_conn.close()
            if best_device is None:
                logging.warn('No serial port found!')
            else:
                ser_conn.port = best_device
                try:
                    ser_conn.open()
                    sel.register(ser_conn, selectors.EVENT_READ, serial_read)
                    logging.info('Connected to serial port %s', best_device)
                    current_device = best_device
                except serial.serialutil.SerialException:
                    # sometimes the device becomes unavailable between getDevice() and open()
                    # just try again next time
                    logging.warn('Could not connect to serial port %s', best_device)

        events = sel.select(SELECTOR_TIMEOUT)
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)

    ser_conn.close()
    control_sock.close()
    serial_sock.close()
