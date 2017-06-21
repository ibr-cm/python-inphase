#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from inphase import Experiment
from inphase.math import calculateDistance

import unittest
import os
THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class UnitTest(unittest.TestCase):

    def setUp(self):
        # load sample measurement
        self.e = Experiment(os.path.join(THIS_DIR, 'testdata/math_data/experiment.yml'))

    def test_calculateDistanceReal(self):
        fft_bins = 1024
        distance, extra_data = calculateDistance(self.e.measurements[0], calc_type='real', fft_bins=fft_bins)

        self.assertAlmostEqual(distance, 24966.18043, places=5)
        self.assertAlmostEqual(extra_data['dqi'], 3109082.67547, places=5)
        self.assertEqual(extra_data['autocorrelation'].size, len(self.e.measurements[0]['samples'])-1)
        self.assertEqual(extra_data['fft'].size, int(fft_bins/2))

    def test_calculateDistanceComplex(self):
        fft_bins = 1024
        distance, extra_data = calculateDistance(self.e.measurements[0], calc_type='complex', fft_bins=fft_bins)

        self.assertAlmostEqual(distance, 24673.41436, places=5)
        self.assertAlmostEqual(extra_data['dqi'], 77.00836, places=5)
        self.assertEqual(extra_data['complex_signal'].size, len(self.e.measurements[0]['samples']))
        self.assertEqual(extra_data['fft'].size, int(fft_bins))


if __name__ == "__main__":
    unittest.main()