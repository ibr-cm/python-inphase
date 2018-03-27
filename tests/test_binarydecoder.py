#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import inphase
from inphase.binarydecoder import SERIAL_FRAME_START, SERIAL_FRAME_END, SERIAL_ESCAPE_BYTE, SERIAL_ESCAPE_ADD
from inphase.binarydecoder import _unescape

import unittest
import os
THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class UnitTest(unittest.TestCase):

    def setUp(self):
        with open(os.path.join(THIS_DIR, 'testdata/serial_data/test_13.txt'), 'rb') as f:
            self.serial_data = f.read()

        with open(os.path.join(THIS_DIR, 'testdata/serial_data/serial_dump_version2_rssi.txt'), 'rb') as f:
            self.serial_data_v2 = f.read()

        self.clean_reference = b'INGA revison not set, defaults to REV=1.4\n../tools/sky/serialdump-linux -b38400 /dev/ttyUSB0\n`\x00\xc8i\x05\x00\x00\x00\x01*6\xa0\xe40E\x84\xfa|M\x1b$a\\\x92Ps\xcc\xfaV\xb9\xebI\xb7\x16\x08k\xf0\xa6\x1bb2\x9b\xd0c\'\xe5\\\xcb"\xe8\x87\rM\xb1\x13\xff@.\xf1\x00\x07Q@.G\xabc}/\x00\xe6\xd9i\x07\x1c\x86/\x1cQ~\xc9\x92\xe3\x1eA\x8d\x93\xd7\xfd:\xe6\x97\x8b\xa2\xeeN\x93\xb92\x8b\xb5!\x8f\xea\x1d1V\xc3\xdf,a\xe8-Y\xfa-U\xae\x12i\xc2\x12y\x94\xf8D\xc1\xe4N\x85\xe3\xddPc\xd1s\x15\xcf\x82\x19G\xe6\x96\xf3\xff@0Tc\x9a\xd7\xf1\x088u\xb0\xc6\xd7\xfa\x195N\x87\xfe\xe0\x1c\x10\x95\xa4\xd9\x14gy\xb2-\xaf$\xde\t\xcc\x03\x9f{\x0ej\xa1\xc7\xde`[\xbc1\xd2\xe1@.z\xc1^\x81\xb1\xda(Ae\x96\xeaW{\xba\xd6z5>540(0)s\r\nNever-used stack > 11770 bytes\r\n600(0)s\r\n'

        self.remaining_reference = b"<\x01\x00\t`\x00\xc8x\x04\x00\x00\x00\x01\xdc\xf4@.c\xfc\xd0\x154O\xab\xf4\xfbt\xf9\x03\xf1,48\x9c\xa6\xfc\xb0*\xc6\xcf]\xbb\xf2?&\x17oI\xec5\xe5:*\x04\x91\x049/\x85\xc7\xdfH\xd6D\xa3 \x81\xeb\x12,$,e\xf2\xb1\x05:L\x86\xca\xf9Y\x01h\xe7)\x196\xc5\xe6\x95\xf8y\xe9\x97\x9eJ\x96[%*)\xa3D\x0e18\xf8\x0cx\xcd\\\xbb\xd3../platform/inga/Makefile.inga:221: recipe for target 'login' failed\n"

    def test_full_clean_output_v2(self):
        with open(os.path.join(THIS_DIR, 'testdata/serial_data/serial_dump_version2_rssi.txt'), 'rb') as f:
            input_data = f.read()

        measurements, remaining_data, clean_data = inphase.decodeBinary(input_data)

        self.assertEqual(len(measurements), 20)

    def test_full_clean_output(self):
        with open(os.path.join(THIS_DIR, 'testdata/serial_data/inphasectl_single_shot.txt'), 'rb') as f:
            input_data = f.read()
        with open(os.path.join(THIS_DIR, 'testdata/serial_data/inphasectl_single_shot_clean.txt'), 'rb') as f:
            output_data = f.read()

        with self.assertLogs('inphase.binarydecoder', level='ERROR') as cm:
            measurements, remaining_data, clean_data = inphase.decodeBinary(input_data)
        self.assertEqual(cm.output, [
            'ERROR:inphase.binarydecoder:unknown protocol version, version field is: 13'
        ])

        self.assertEqual(len(measurements), 1)
        self.assertEqual(clean_data, output_data)

    def test_only_bin_data(self):
        with open(os.path.join(THIS_DIR, 'testdata/serial_data/inphasectl_single_shot_bindata_only.bin'), 'rb') as f:
            input_data = f.read()
        measurements, remaining_data, clean_data = inphase.decodeBinary(input_data)

        self.assertEqual(len(measurements), 1)
        self.assertEqual(clean_data, b'')

    def test_cmd_output(self):
        with open(os.path.join(THIS_DIR, 'testdata/serial_data/inphasectl_commands.txt'), 'rb') as f:
            input_data = f.read()

        with self.assertLogs('inphase.binarydecoder', level='ERROR') as cm:
            measurements, remaining_data, clean_data = inphase.decodeBinary(input_data)
        self.assertEqual(cm.output, [
            'ERROR:inphase.binarydecoder:frame invalid! length was: 3, minimum length is: 12',
            'ERROR:inphase.binarydecoder:frame invalid! length was: 7, minimum length is: 12',
            'ERROR:inphase.binarydecoder:frame invalid! length was: 3, minimum length is: 12',
            'ERROR:inphase.binarydecoder:frame invalid! length was: 7, minimum length is: 12'
        ])

        self.assertEqual(len(measurements), 0)
        self.assertEqual(clean_data, input_data)

    def test_full_clean_output_broken(self):
        with open(os.path.join(THIS_DIR, 'testdata/serial_data/inphasectl_single_shot_broken.txt'), 'rb') as f:
            input_data = f.read()
        with open(os.path.join(THIS_DIR, 'testdata/serial_data/inphasectl_single_shot_broken_clean.txt'), 'rb') as f:
            output_data = f.read()

        with self.assertLogs('inphase.binarydecoder', level='ERROR') as cm:
            measurements, remaining_data, clean_data = inphase.decodeBinary(input_data)
        self.assertEqual(cm.output, [
            'ERROR:inphase.binarydecoder:unknown protocol version, version field is: 13'
        ])

        self.assertEqual(len(measurements), 1)
        self.assertEqual(clean_data, output_data)

    def test_all_clean_before_start(self):
        test_data = b'>>-- inphasectl --<<'
        correct_clean = b'>>-- inphasectl --<'
        measurements, remaining_data, clean = inphase.decodeBinary(test_data)
        self.assertEqual(len(measurements), 0)
        self.assertEqual(clean, correct_clean)
        self.assertEqual(len(remaining_data), 1)

    def test_invalid_frame(self):
        test_data = b'<>'
        with self.assertLogs('inphase.binarydecoder', level='ERROR') as cm:
            measurements, remaining_data, clean = inphase.decodeBinary(test_data)
        self.assertEqual(cm.output, [
            'ERROR:inphase.binarydecoder:frame invalid! no data between start and stop symbol.'
        ])
        self.assertEqual(len(measurements), 0)
        self.assertEqual(clean, test_data)
        self.assertEqual(len(remaining_data), 0)

    def test_parsing(self):
        # split serial data into pieces of 10 bytes
        data_pieces = [self.serial_data[i:i + 10] for i in range(0, len(self.serial_data), 10)]
        remaining_data = bytes()
        measurements = list()
        clean_data = bytearray()
        for d in data_pieces:
            remaining_data += d
            m, remaining_data, c = inphase.decodeBinary(remaining_data)
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
