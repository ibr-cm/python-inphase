#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from inphase import Experiment, calcDistFFT, calcDistFFTDetailed, calcDistComplexDetailed

import unittest
import os
THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class UnitTest(unittest.TestCase):

    def setUp(self):
        # load sample measurement
        self.e = Experiment(os.path.join(THIS_DIR, 'testdata/math_data/experiment.yml'))

    def test_calcDistFFT(self):
        distance, dqi = calcDistFFT(self.e.measurements[0])
        self.assertAlmostEqual(distance, 24966.18043, places=5)
        self.assertAlmostEqual(dqi, 3109082.67547, places=5)

    def test_calcDistFFTDetailed(self):
        fft_bins = 1024
        distance, dqi, autocorr_data, fft_data = calcDistFFTDetailed(self.e.measurements[0], fft_bins=fft_bins)

        self.assertAlmostEqual(distance, 24966.18043, places=5)
        self.assertAlmostEqual(dqi, 3109082.67547, places=5)
        self.assertEqual(autocorr_data.size, len(self.e.measurements[0]['samples'])-1)
        self.assertEqual(fft_data.size, int(fft_bins/2))

    def test_calcDistComplexDetailed(self):
        fft_bins = 1024
        distance, dqi, complex_data, fft_data = calcDistComplexDetailed(self.e.measurements[0], fft_bins=fft_bins)

        self.assertAlmostEqual(distance, 24673.41436, places=5)
        self.assertAlmostEqual(dqi, 77.00836, places=5)
        self.assertEqual(complex_data.size, len(self.e.measurements[0]['samples']))
        self.assertEqual(fft_data.size, int(fft_bins))


if __name__ == "__main__":
    unittest.main()
