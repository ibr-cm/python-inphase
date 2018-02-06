#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from inphase import CutoffDecimator, PMUNoise, MRLADecimator, MRLAInterpolator, Experiment
from inphase.math import calculateDistance

import unittest
import os
THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class UnitTest(unittest.TestCase):

    def setUp(self):
        self.e = Experiment(os.path.join(THIS_DIR, 'testdata/math_data/clean_sawtooth.yml'))

    def test_CutoffDecimator(self):
        m = self.e.measurements[0]

        reference_distance, extra_data = calculateDistance(m, calc_type='complex', fft_bins=4096)

        decimator = CutoffDecimator(10)
        decimator.modify(m)
        self.assertEqual(len(m['samples']), 10)

        cutoff_distance, extra_data = calculateDistance(m, calc_type='complex', fft_bins=4096)
        self.assertAlmostEqual(reference_distance, cutoff_distance)

    def test_PMUNoise(self):
        m = self.e.measurements[0]

        reference_distance, extra_data = calculateDistance(m, calc_type='complex', fft_bins=4096)

        decimator = PMUNoise()
        decimator.modify(m)
        self.assertEqual(len(m['samples']), 200)

        cutoff_distance, extra_data = calculateDistance(m, calc_type='complex', fft_bins=4096)
        self.assertAlmostEqual(reference_distance, cutoff_distance)

    def test_MRLADecimator(self):
        m = self.e.measurements[0]

        reference_distance, extra_data = calculateDistance(m, calc_type='complex', fft_bins=4096)

        decimator = MRLADecimator()
        decimator.modify(m)
        self.assertEqual(len(m['samples']), 25)  # a MRLA of length 199 has 25 antennas
        interpolator = MRLAInterpolator()
        interpolator.modify(m)
        self.assertEqual(len(m['samples']), 200)

        # test if samples are 0.5 MHz apart after interpolation
        for a, b in zip(m['samples'][:-1], m['samples'][1:]):  # iterate pairwise over samples
            freq_delta = b['frequency'] - a['frequency']
            self.assertAlmostEqual(freq_delta, 0.5)

        # test if distance from interpolated signal is the same as before
        interpolated_distance, extra_data = calculateDistance(m, calc_type='complex', fft_bins=4096)
        self.assertAlmostEqual(reference_distance, interpolated_distance)


if __name__ == "__main__":
    unittest.main()
