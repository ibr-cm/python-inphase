#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import os
import logging

HOST = 'localhost'
PORT = 50005
THIS_DIR = os.path.dirname(os.path.abspath(__file__))

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


def send_measurements(conn):
    with open(os.path.join(THIS_DIR, 'testdata/serial_data/test_13.txt'), 'rb') as f:
        logger.info("sending file")
        conn.send(f.read())
        logger.info("end of file")


def main():
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        conn, addr = s.accept()
        with conn:
            logger.info('Connected by', addr)
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                lines = data.splitlines()
                for line in lines:
                    command = line.split(b' ', 4)
                    if command[0] == b'inphasectl' and len(command) > 2:
                        logger.info("command received", command[1:])
                        param = command[2].decode()
                        if command[1] == b'get':
                            if param in settings:
                                value = settings[param]
                                conn.send(
                                    param.encode()+b':'+str(value).encode()+b'\r\n')
                            else:
                                logger.info("param", param, "not in", settings)
                                conn.send(
                                    b'err: unknown parameter '+command[2]+b'\r\n')
                        elif command[1] == b'set':
                            value = command[3]
                            try:
                                settings[param] = int(value.decode())
                            except ValueError:
                                settings[param] = value.decode()
                            conn.send(
                                param.encode()+b':'+str(settings[param]).encode()+b'\r\n')
                            logger.info("param", param, "value", value)
                            if param == 'distance_sensor0.start' and settings[param] == 1:
                                send_measurements(conn)
                                conn.send(b'\r\ndistance_sensor0.start:0\r\n')
                        else:
                            logger.info("command dropped.")

            conn.close()

if __name__ == "__main__":
    main()
