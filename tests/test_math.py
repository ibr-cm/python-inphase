#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from inphase import Experiment
from inphase.math import calc_fft_spectrum
from inphase.math import substract_provided_offsets
from inphase.math import calculateDistance, calculateDistances
from inphase.dataformat import Measurement, Node

import numpy as np

import unittest
import os
THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class UnitTest(unittest.TestCase):

    def setUp(self):
        # load sample measurement
        self.e = Experiment(os.path.join(THIS_DIR, 'testdata/math_data/experiment.yml'))
        self.e_rssi = Experiment(os.path.join(THIS_DIR, 'testdata/math_data/experiment_rssi.yml'))

    def test_calc_fft_spectrum(self):
        fft_bins = 1024
        # test real
        fft, extra_data = calc_fft_spectrum(self.e.measurements[0],
                                            calc_type='real',
                                            fft_bins=fft_bins)

        self.assertEqual(np.argmax(fft), 89)
        self.assertAlmostEqual(np.max(fft), 3109082.67547, places=5)
        self.assertEqual(extra_data['autocorrelation'].size,
                         len(self.e.measurements[0]['samples']) - 1)
        self.assertEqual(fft.size, int(fft_bins / 2))
        # test complex
        fft, extra_data = calc_fft_spectrum(self.e.measurements[0],
                                            calc_type='complex',
                                            fft_bins=fft_bins)

        self.assertEqual(np.argmax(fft), 88)
        self.assertAlmostEqual(np.max(fft), 77.00836, places=5)
        self.assertEqual(extra_data['complex_signal'].size,
                         len(self.e.measurements[0]['samples']))
        self.assertEqual(extra_data['complex_signal'].size,
                         len(self.e.measurements[0]['samples']))
        self.assertEqual(fft.size, int(fft_bins))
        # test complex_with_magnitude
        fft, extra_data = calc_fft_spectrum(self.e_rssi.measurements[0],
                                            calc_type='complex_with_magnitude',
                                            fft_bins=fft_bins)

        self.assertEqual(np.argmax(fft), 9)
        self.assertAlmostEqual(np.max(fft), 0.00649, places=5)
        self.assertEqual(extra_data['complex_signal'].size,
                         len(self.e.measurements[0]['samples']))
        self.assertEqual(extra_data['complex_signal'].size,
                         len(self.e.measurements[0]['samples']))
        self.assertEqual(fft.size, int(fft_bins))

    def test_substract_provided_offset(self):
        OFFSET = 1000
        REF_DISTANCE = 2000
        for role in ['initiator', 'reflector']:
            measurement = Measurement()
            measurement[role] = Node()
            measurement[role]['antenna_offset'] = OFFSET
            self.assertEqual(substract_provided_offsets(measurement, REF_DISTANCE),
                             1000)
            self.assertTrue(np.isnan(substract_provided_offsets(measurement,
                                                                np.nan)))

    def test_calculateDistanceReal(self):
        fft_bins = 1024
        distance, extra_data = calculateDistance(self.e.measurements[0], calc_type='real', fft_bins=fft_bins)

        self.assertAlmostEqual(distance, 24966.18043, places=5)
        self.assertAlmostEqual(extra_data['dqi'], 3109082.67547, places=5)
        self.assertEqual(extra_data['autocorrelation'].size, len(self.e.measurements[0]['samples']) - 1)
        self.assertEqual(extra_data['fft'].size, int(fft_bins / 2))

    def test_calculateDistanceComplex(self):
        fft_bins = 1024
        distance, extra_data = calculateDistance(self.e.measurements[0], calc_type='complex', fft_bins=fft_bins)

        self.assertAlmostEqual(distance, 24673.41436, places=5)
        self.assertAlmostEqual(extra_data['dqi'], 77.00836, places=5)
        self.assertEqual(extra_data['complex_signal'].size, len(self.e.measurements[0]['samples']))
        self.assertEqual(extra_data['fft'].size, int(fft_bins))

    def test_calculateDistanceComplexWithMagnitude(self):
        fft_bins = 1024
        distance, extra_data = calculateDistance(self.e_rssi.measurements[0], calc_type='complex_with_magnitude', fft_bins=fft_bins)

        self.assertAlmostEqual(distance, 2634.89465, places=5)
        self.assertAlmostEqual(extra_data['dqi'], 0.00649, places=5)
        self.assertEqual(extra_data['complex_signal'].size, len(self.e.measurements[0]['samples']))
        self.assertEqual(extra_data['fft'].size, int(fft_bins))

    def test_calculateDistanceRealInterpolated(self):
        clean_sawtooth = Experiment(os.path.join(THIS_DIR, 'testdata/math_data/clean_sawtooth_low_dist.yml'))
        fft_bins = 1024
        with self.assertRaises(NotImplementedError):
            distance, extra_data = calculateDistance(clean_sawtooth.measurements[0], calc_type='real', fft_bins=fft_bins, interpolation='unknown')

        distance, extra_data = calculateDistance(clean_sawtooth.measurements[0], calc_type='real', fft_bins=fft_bins, interpolation='parabolic')

        self.assertAlmostEqual(distance, 10036.53897, places=5)
        self.assertAlmostEqual(extra_data['dqi'], 31213619.47735, places=5)

    def test_calculateDistanceComplexInterpolated(self):
        clean_sawtooth = Experiment(os.path.join(THIS_DIR, 'testdata/math_data/clean_sawtooth.yml'))
        fft_bins = 1024
        with self.assertRaises(NotImplementedError):
            distance, extra_data = calculateDistance(clean_sawtooth.measurements[0], calc_type='complex', fft_bins=fft_bins, interpolation='unknown')

        distance, extra_data = calculateDistance(clean_sawtooth.measurements[0], calc_type='complex', fft_bins=fft_bins, interpolation='parabolic')

        self.assertAlmostEqual(distance, 150095.021346, places=5)
        self.assertAlmostEqual(extra_data['dqi'], 199.89610, places=5)

    def test_calculateDistanceComplexWithMagnitudeInterpolated(self):
        fft_bins = 1024
        with self.assertRaises(NotImplementedError):
            distance, extra_data = calculateDistance(self.e_rssi.measurements[0], calc_type='complex_with_magnitude', fft_bins=fft_bins, interpolation='unknown')

        distance, extra_data = calculateDistance(self.e_rssi.measurements[0], calc_type='complex_with_magnitude', fft_bins=fft_bins, interpolation='parabolic')

        self.assertAlmostEqual(distance, 2722.81638, places=5)
        self.assertAlmostEqual(extra_data['dqi'], 0.00652, places=5)

    def test_calculateDistanceComplexOddFFT(self):
        clean_sawtooth = Experiment(os.path.join(THIS_DIR, 'testdata/math_data/clean_sawtooth.yml'))
        distance0, extra_data = calculateDistance(clean_sawtooth.measurements[0], calc_type='complex', fft_bins=16)
        distance1, extra_data = calculateDistance(clean_sawtooth.measurements[0], calc_type='complex', fft_bins=17)
        distance2, extra_data = calculateDistance(clean_sawtooth.measurements[0], calc_type='complex', fft_bins=18)

        self.assertAlmostEqual(distance0, distance2, places=5)
        self.assertAlmostEqual(distance0, distance1, places=5)
        self.assertAlmostEqual(distance1, distance2, places=5)

    def test_calculateDistances(self):
        fft_bins = 1024
        clean_mixed_sawtooth = Experiment(os.path.join(THIS_DIR, 'testdata/math_data/clean_sawtooth_mixed_dist.yml'))
        distances, extra_data = calculateDistances(clean_mixed_sawtooth.measurements[0], calc_type='complex',
                                                   multi_max=True, fft_bins=fft_bins, interpolation='parabolic')
        self.assertEqual(len(distances), 2)
        self.assertEqual(len(extra_data['maxima']), 2)
        self.assertEqual(len(extra_data['dqis']), 2)
        self.assertAlmostEqual(distances[0], 9972.24512, places=5)
        self.assertAlmostEqual(distances[1], 100011.75616, places=5)
        self.assertAlmostEqual(extra_data['dqis'][0], 100.15191, places=5)
        self.assertAlmostEqual(extra_data['dqis'][1], 100.12582, places=5)

    def test_notImplemented(self):
        with self.assertRaises(NotImplementedError):
            distance, extra_data = calculateDistance(self.e.measurements[0], calc_type='foobar')

    def test_dcThreshold(self):
        fft_bins = 1024
        distance, extra_data = calculateDistance(self.e.measurements[0], calc_type='complex', fft_bins=fft_bins, dc_threshold=89)

        self.assertTrue(np.isnan(distance))
        self.assertEqual(extra_data['dqi'], 0)


if __name__ == "__main__":
    unittest.main()
