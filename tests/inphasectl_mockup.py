#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import os
import logging

HOST = 'localhost'
PORT = 50005
THIS_DIR = os.path.dirname(os.path.abspath(__file__))

s = None

logger = logging.getLogger(__name__)

settings = dict()
settings['distance_sensor0.allow_ranging'] = 1
settings['distance_sensor0.count'] = 3
settings['distance_sensor0.initiator'] = 0xc39f
settings['distance_sensor0.output'] = 2
settings['distance_sensor0.start'] = 0
settings['distance_sensor0.target'] = 0xdb98
settings['default.version'] = 'inphasectl-mockup'

# TODO add the pmu parameters
# .max_freq = 2600,
# .num_frequencies = 100};
# .num_samples = 10,
# .start_freq = 2400,


def send_measurements(conn, number_of_measurements):
    with open(os.path.join(THIS_DIR, 'testdata/serial_data/inphasectl_single_shot_bindata_only.bin'), 'rb') as f:
        logger.info("Sending measurements from file")
        measurement_data = f.read()
        for counter in range(number_of_measurements):
            logger.info("Measurement #%d", counter)
            conn.send(measurement_data)
        logger.info("Sending done")


def main():
    global s
    with socket.socket() as s:
        running = True
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        try:
            conn, addr = s.accept()
        except OSError:
            pass
        else:
            with conn:
                logger.info('Connected by %s', addr)
                while running:
                    data = conn.recv(1024)
                    if not data:
                        break
                    lines = data.splitlines()
                    for line in lines:
                        command = line.split(b' ', 4)
                        if command[0] == b'inphasectl' and len(command) > 2:
                            logger.info("command received %s", command[1:])
                            param = command[2].decode()
                            if command[1] == b'get':
                                if param in settings:
                                    value = settings[param]
                                    conn.send(param.encode()+b':'+str(value).encode()+b'\r\n')
                                else:
                                    logger.info("param %s not in %s", param, settings)
                                    conn.send(b'err: unknown parameter '+command[2]+b'\r\n')
                            elif command[1] == b'set':
                                value = command[3]
                                try:
                                    settings[param] = int(value.decode())
                                except ValueError:
                                    settings[param] = value.decode()
                                conn.send(param.encode()+b':'+str(settings[param]).encode()+b'\r\n')
                                logger.debug("param %s value %s", param, value)
                                if param == 'distance_sensor0.start' and settings[param] == 1:
                                    send_measurements(conn, settings['distance_sensor0.count'])
                                    conn.send(b'\r\ndistance_sensor0.start:0\r\n')
                            elif command[1] == b'list-devices':
                                send_list(conn, devices)
                            elif command[1] == b'list-parameters':
                                # TODO get device if set in command
                                send_list(conn, devices)
                            else:
                                logger.info("command dropped.")
            logger.info('Connection closed by %s', addr)

if __name__ == "__main__":
    import signal

    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    # TODO: use CONSTANT from inphase module
    formatter = logging.Formatter('%(name)s/%(funcName)s (%(threadName)s) - %(levelname)s - %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)

    def signal_handler(signal, frame):
        global running, s
        logger.info('Exiting...')
        running = False
        if s:
            s.close()

    signal.signal(signal.SIGINT, signal_handler)

    main()
