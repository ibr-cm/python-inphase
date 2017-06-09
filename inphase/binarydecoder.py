#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataformat import Measurement, Node, Sample

import unittest
from struct import unpack, calcsize
import time

# as defined in at86rf233.c
SERIAL_FRAME_START     = 0x3C      # "<" in ascii
SERIAL_FRAME_END       = 0x3E      # ">" in ascii
SERIAL_ESCAPE_BYTE     = 0x40      # "@" in ascii
SERIAL_ESCAPE_ADD      = 0x10      # add this to byte after escape


def decodeBinary(data, timestamp=True):
    """Returns parsed measurements from binary data, also returns remaining data that still needs parsing and clean data that does not contain any other binary data."""
    measurements = list()
    remaining_data = data
    clean_data = bytearray()

    while True:
        start = remaining_data.find(SERIAL_FRAME_START)
        end = remaining_data.find(SERIAL_FRAME_END, start)

        if start == -1:
            # no start byte detected
            break
        if end == -1:
            # no end byte detected
            break

        # if we reach this, next frame is found

        # remove data before the frame from remaining data, it does not contain any more binary frames
        clean_data += remaining_data[0:start]
        # extract frame from remaining data
        raw_frame = remaining_data[start:end+1]
        # remaining data is now everything after the current frame
        remaining_data = remaining_data[end+1:]

        # now parse the frame contents
        frame = bytearray(raw_frame)

        # remove all byte stuffing instances
        frame = _unescape(frame)

        # unpack the byte sin the frame
        measurement_data = _parsePacket(frame)

        if not measurement_data:
            # frame was invalid, this means byte were lost on serial connection or we found frame delimiter that do not actually delimit a frame at all
            # add the frame to clean_data, as it is not a valid frame and might contain other output
            clean_data += raw_frame
            continue

        # set up a measurement in the correct data format
        reflector = Node({
            'uid': measurement_data['reflector_address']
            })

        samples = list()

        for freq, values in zip(measurement_data['frequencies'], measurement_data['values']):
            samples.append(Sample({
                'frequency': freq,
                'pmu_values': values
                }))

        measurement = Measurement({
            'dqi': measurement_data['dist_quality'],
            'measured_distance': measurement_data['dist_meter'] * 1000 + measurement_data['dist_centimeter'] * 10,
            'reflector': reflector,
            'samples': samples
            })

        if timestamp:
            measurement['timestamp'] = time.time()

        measurements.append(measurement)

    return measurements, remaining_data, clean_data


def _unescape(frame):
    # find all escape bytes
    indices = [i for i, x in enumerate(frame) if x == SERIAL_ESCAPE_BYTE]

    # unescape all bytes after escape bytes
    for i in indices:
        frame[i+1] = (frame[i+1] + SERIAL_ESCAPE_ADD) % 256

    # remove all escape bytes fround in the first step
    frame = bytearray([i for j, i in enumerate(frame) if j not in indices])

    return frame


def _parsePacket(frame):
    # remove frame delimiter
    frame = frame[1:-1]

    data = dict()

    unpack_str = '>BB'
    samples, step = unpack(unpack_str, frame[0:calcsize(unpack_str)])

    unpack_str_2 = '>3H4B'
    frequency_start, measurements, reflector_address, dist_meter, dist_centimeter, dist_quality, status = unpack(unpack_str_2, frame[calcsize(unpack_str):calcsize(unpack_str)+calcsize(unpack_str_2)])

    if (step == 0):  # by definition 0 step size is 0.5
        step = 0.5

    value_offset = calcsize(unpack_str)+calcsize(unpack_str_2)

    expected_frame_length = measurements * samples + value_offset

    if (expected_frame_length != len(frame)):
        print("frame invalid! length was:", len(frame), ", expected length is:", expected_frame_length)
        return None

    data['measurements'] = measurements
    data['samples'] = samples
    data['step'] = step
    data['reflector_address'] = reflector_address
    data['dist_meter'] = dist_meter
    data['dist_centimeter'] = dist_centimeter
    data['dist_quality'] = dist_quality
    data['status'] = status

    #print data

    data['frequencies'] = list()

    for i in range(measurements):
        data['frequencies'].append(frequency_start + i * step)

    data['values'] = list()
    values = unpack('>' + str(measurements*samples) + 'b', frame[value_offset:])

    for i in range(measurements):
        data['values'].append(list())
        for j in range(samples):
            data['values'][i].append(values[i*samples+j])

    return data


class UnitTest(unittest.TestCase):

    def setUp(self):
        with open('testdata/serial_data/test_13.txt', 'rb') as f:
            self.serial_data = f.read()

        self.clean_reference = b'INGA revison not set, defaults to REV=1.4\n../tools/sky/serialdump-linux -b38400 /dev/ttyUSB0\n`\x00\xc8i\x05\x00\x00\x00\x01*6\xa0\xe40E\x84\xfa|M\x1b$a\\\x92Ps\xcc\xfaV\xb9\xebI\xb7\x16\x08k\xf0\xa6\x1bb2\x9b\xd0c\'\xe5\\\xcb"\xe8\x87\rM\xb1\x13\xff@.\xf1\x00\x07Q@.G\xabc}/\x00\xe6\xd9i\x07\x1c\x86/\x1cQ~\xc9\x92\xe3\x1eA\x8d\x93\xd7\xfd:\xe6\x97\x8b\xa2\xeeN\x93\xb92\x8b\xb5!\x8f\xea\x1d1V\xc3\xdf,a\xe8-Y\xfa-U\xae\x12i\xc2\x12y\x94\xf8D\xc1\xe4N\x85\xe3\xddPc\xd1s\x15\xcf\x82\x19G\xe6\x96\xf3\xff@0Tc\x9a\xd7\xf1\x088u\xb0\xc6\xd7\xfa\x195N\x87\xfe\xe0\x1c\x10\x95\xa4\xd9\x14gy\xb2-\xaf$\xde\t\xcc\x03\x9f{\x0ej\xa1\xc7\xde`[\xbc1\xd2\xe1@.z\xc1^\x81\xb1\xda(Ae\x96\xeaW{\xba\xd6z5>540(0)s\r\nNever-used stack > 11770 bytes\r\n600(0)s\r\n'

        self.remaining_reference = b"<\x01\x00\t`\x00\xc8x\x04\x00\x00\x00\x01\xdc\xf4@.c\xfc\xd0\x154O\xab\xf4\xfbt\xf9\x03\xf1,48\x9c\xa6\xfc\xb0*\xc6\xcf]\xbb\xf2?&\x17oI\xec5\xe5:*\x04\x91\x049/\x85\xc7\xdfH\xd6D\xa3 \x81\xeb\x12,$,e\xf2\xb1\x05:L\x86\xca\xf9Y\x01h\xe7)\x196\xc5\xe6\x95\xf8y\xe9\x97\x9eJ\x96[%*)\xa3D\x0e18\xf8\x0cx\xcd\\\xbb\xd3../platform/inga/Makefile.inga:221: recipe for target 'login' failed\n"

    def test_parsing(self):
        # split serial data into pieces of 10 bytes
        data_pieces = [self.serial_data[i:i+10] for i in range(0, len(self.serial_data), 10)]
        remaining_data = bytes()
        measurements = list()
        clean_data = bytearray()
        for d in data_pieces:
            remaining_data += d
            m, remaining_data, c = decodeBinary(remaining_data)
            clean_data += c
            measurements += m

        self.assertEqual(len(measurements), 665)
        self.assertEqual(len(measurements[100]['samples']), 200)
        self.assertEqual(measurements[100]['reflector']['uid'], 9476)
        self.assertEqual(clean_data, self.clean_reference)
        self.assertEqual(remaining_data, self.remaining_reference)

    def test_unescape(self):
        frame = bytearray([ord(b'<'), SERIAL_ESCAPE_BYTE, SERIAL_ESCAPE_BYTE-SERIAL_ESCAPE_ADD, SERIAL_ESCAPE_BYTE, SERIAL_FRAME_START-SERIAL_ESCAPE_ADD, SERIAL_ESCAPE_BYTE, SERIAL_FRAME_END-SERIAL_ESCAPE_ADD, ord(b'>')])
        result = bytearray([ord(b'<'), SERIAL_ESCAPE_BYTE, SERIAL_FRAME_START, SERIAL_FRAME_END, ord(b'>')])
        self.assertEqual(_unescape(frame), result)


if __name__ == "__main__":
    unittest.main()
