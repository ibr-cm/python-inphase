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
        particle_count = 10000
        world = inphase.localization.particlefilter.World((-2000, 1000), (-250, 1500), (0, 700))
        particlefilter = inphase.localization.particlefilter.ParticleFilter(world, particle_count=particle_count)

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

        # weight particles
        particlefilter.weight('Anchor', [500, 100, 200], 0, 1000)

        self.assertAlmostEqual(np.sum(particlefilter.weights), 1)  # sum must be 1
        self.assertEqual(len(particlefilter.weights), particle_count)  # must match the number of particles

    def test_ParticleFilterLocalization(self):
        world = inphase.localization.particlefilter.World((-2000, 1000), (-250, 1500), (0, 700))
        particlefilter = inphase.localization.particlefilter.ParticleFilter(world)


        for _ in range(50):
            particlefilter.tick('Anchor 1', [500, 100, 200], 0, 1000)
            particlefilter.tick('Anchor 2', [100, 100, 200], 400, 1000)
            particlefilter.tick('Anchor 3', [500, 100, -300], 500, 1000)

        self.assertAlmostEqual(particlefilter.tag_position[0], 506.97, 2)
        self.assertAlmostEqual(particlefilter.tag_position[1], 97.02, 2)
        self.assertAlmostEqual(particlefilter.tag_position[2], 197.82, 2)
        self.assertAlmostEqual(particlefilter.particle_quality, 1.01996, 5)


if __name__ == "__main__":
    unittest.main()
