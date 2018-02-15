#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import inphase

import numpy as np

import unittest
import os
THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class UnitTest(unittest.TestCase):

    def setUp(self):
        np.random.seed(0)  # make randomness predicatable

    def test_World(self):
        world = inphase.localization.particlefilter.World((-2000, 1000), (-250, 1500), (0, 700))
        np.testing.assert_array_equal(world.dimensions_min, np.array([-2000, -250, 0]))
        np.testing.assert_array_equal(world.dimensions_max, np.array([1000, 1500, 700]))

    def test_ParticleFilterImplementation(self):
        world = inphase.localization.particlefilter.World((-2000, 1000), (-250, 1500), (0, 700))
        particlefilter = inphase.localization.particlefilter.ParticleFilter(world, particle_count=10000)

        # check if particles are inside world
        for position in particlefilter.positions:
            for pos, wmin, wmax in zip(position, world.dimensions_min, world.dimensions_max):
                self.assertGreaterEqual(pos, wmin)
                self.assertLessEqual(pos, wmax)

        # move particles
        particlefilter.predict()

        # check if particles are inside world after move
        for position in particlefilter.positions:
            for pos, wmin, wmax in zip(position, world.dimensions_min, world.dimensions_max):
                self.assertGreaterEqual(pos, wmin)
                self.assertLessEqual(pos, wmax)

    def test_ParticleFilterLocalization(self):
        world = inphase.localization.particlefilter.World((-2000, 1000), (-250, 1500), (0, 700))
        particlefilter = inphase.localization.particlefilter.ParticleFilter(world)

        for _ in range(50):
            particlefilter.tick([500, 100, 200], 0, 1000)
            particlefilter.tick([100, 100, 200], 400, 1000)
            particlefilter.tick([500, 100, -300], 500, 1000)

        self.assertAlmostEqual(particlefilter.tag_position[0], 529.49414, 5)
        self.assertAlmostEqual(particlefilter.tag_position[1], 135.80492, 5)
        self.assertAlmostEqual(particlefilter.tag_position[2], 232.58776, 5)
        self.assertAlmostEqual(particlefilter.particle_quality, 1.01744, 5)


if __name__ == "__main__":
    unittest.main()
