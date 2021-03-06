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

    def test_World_2D(self):
        world = inphase.localization.particlefilter.World((-2000, 1000), (-250, 1500))
        np.testing.assert_array_equal(world.dimensions_min, np.array([-2000, -250, 0]))
        np.testing.assert_array_equal(world.dimensions_max, np.array([1000, 1500, 0]))

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
        particlefilter.predict(None)

        # check if particles are still somewhere on the map
        for position in particlefilter.positions:
            for pos, wmin, wmax in zip(position, world.dimensions_min, world.dimensions_max):
                self.assertGreaterEqual(pos, wmin - 10000)
                self.assertLessEqual(pos, wmax + 10000)

        # weight particles
        particlefilter.weight('Anchor', [500, 100, 200], 0, 1)

        self.assertAlmostEqual(np.sum(particlefilter.weights), 1)  # sum must be 1
        self.assertEqual(len(particlefilter.weights), particle_count)  # must match the number of particles

    def test_ParticleFilterLocalization(self):
        world = inphase.localization.particlefilter.World((-2000, 1000), (-250, 1500), (0, 700))
        particlefilter = inphase.localization.particlefilter.ParticleFilter(world)

        max_error = 30  # we tolerate 3 centimeter error for this test

        for _ in range(50):
            particlefilter.tick('Anchor 1', [500, 100, 200], 0, 1)
            particlefilter.tick('Anchor 2', [100, 100, 200], 400, 1)
            particlefilter.tick('Anchor 3', [500, 100, -300], 500, 1)

        self.assertGreaterEqual(particlefilter.tag_position[0], 500 - max_error)
        self.assertLessEqual(particlefilter.tag_position[0], 500 + max_error)

        self.assertGreaterEqual(particlefilter.tag_position[1], 100 - max_error)
        self.assertLessEqual(particlefilter.tag_position[1], 100 + max_error)

        self.assertGreaterEqual(particlefilter.tag_position[2], 200 - max_error)
        self.assertLessEqual(particlefilter.tag_position[2], 200 + max_error)

        self.assertGreaterEqual(particlefilter.particle_quality, 0.95)

    def test_ParticleFilterLocalizationTimestamped(self):
        world = inphase.localization.particlefilter.World((-2000, 1000), (-250, 1500), (0, 700))
        particlefilter = inphase.localization.particlefilter.ParticleFilter(world)

        max_error = 30  # we tolerate 3 centimeter error for this test

        for _ in range(50):
            particlefilter.tick('Anchor 1', [500, 100, 200], 0, 1, timestamp=100)
            particlefilter.tick('Anchor 2', [100, 100, 200], 400, 1, timestamp=102)
            particlefilter.tick('Anchor 3', [500, 100, -300], 500, 1, timestamp=102.5)
            particlefilter.tick('Anchor 3', [500, 100, -300], 500, 1, timestamp=102.4)

        self.assertGreaterEqual(particlefilter.tag_position[0], 500 - max_error)
        self.assertLessEqual(particlefilter.tag_position[0], 500 + max_error)

        self.assertGreaterEqual(particlefilter.tag_position[1], 100 - max_error)
        self.assertLessEqual(particlefilter.tag_position[1], 100 + max_error)

        self.assertGreaterEqual(particlefilter.tag_position[2], 200 - max_error)
        self.assertLessEqual(particlefilter.tag_position[2], 200 + max_error)

        self.assertGreaterEqual(particlefilter.particle_quality, 0.95)

    def test_ParticleFilterLocalization_2DMode(self):
        world = inphase.localization.particlefilter.World((-2000, 1000), (-250, 1500), (0, 700))
        particlefilter = inphase.localization.particlefilter.ParticleFilter(world, dimensions=2)

        max_error = 20  # we tolerate 2 centimeter error for this test

        for _ in range(50):
            particlefilter.tick('Anchor 1', [500, 100, 200], 0, 1)
            particlefilter.tick('Anchor 2', [100, 100, 200], 400, 1)
            particlefilter.tick('Anchor 3', [500, 500], 400, 1)  # z coordinate can be omitted

        self.assertGreaterEqual(particlefilter.tag_position[0], 500 - max_error)
        self.assertLessEqual(particlefilter.tag_position[0], 500 + max_error)

        self.assertGreaterEqual(particlefilter.tag_position[1], 100 - max_error)
        self.assertLessEqual(particlefilter.tag_position[1], 100 + max_error)

        self.assertEqual(particlefilter.tag_position[2], 0)

        self.assertGreaterEqual(particlefilter.particle_quality, 0.95)

    def test_ParticleFilterToString(self):
        world = inphase.localization.particlefilter.World((-2000, 1000), (-250, 1500), (0, 700))
        particlefilter = inphase.localization.particlefilter.ParticleFilter(world)
        self.assertEqual(str(particlefilter), '(0, 0, 0) q=0.000')

    def test_ParticleFilterRandomInit(self):
        particle_count = 10000
        world = inphase.localization.particlefilter.World((-2000, 1000), (-250, 1500), (0, 700))
        particlefilter = inphase.localization.particlefilter.ParticleFilter(world, particle_count=particle_count)

        particlefilter.randomizeParticles(stratified=False)

        # check if particles are inside world
        for position in particlefilter.positions:
            for pos, wmin, wmax in zip(position, world.dimensions_min, world.dimensions_max):
                self.assertGreaterEqual(pos, wmin)
                self.assertLessEqual(pos, wmax)

    def test_ParticleFilterForceHardReset(self):
        world = inphase.localization.particlefilter.World((-2000, 50000), (-250, 75000), (0, 35000))
        particlefilter = inphase.localization.particlefilter.ParticleFilter(world, particle_count=10000)

        max_error = 1000  # we tolerate 100 centimeter error for this test

        for _ in range(10):
            particlefilter.tick('Anchor 1', [0, 0, 0], 0, 1)
            particlefilter.tick('Anchor 2', [100, 0, 0], 100, 1)
            particlefilter.tick('Anchor 3', [0, 0, -300], 300, 1)

        # jump to another location

        with self.assertLogs(inphase.localization.particlefilter.logger, level='WARNING') as cm:
            particlefilter.tick('Anchor 1', [10000, 15000, 7000], 0, 1)

        self.assertEqual(cm.output, ['WARNING:inphase.localization.particlefilter:Particle Filter needed hard reset!'])

        for _ in range(155):
            particlefilter.tick('Anchor 1', [10000, 15000, 7000], 0, 1)
            particlefilter.tick('Anchor 2', [10000, 10000, 7000], 5000, 1)
            particlefilter.tick('Anchor 3', [10000, 15000, 2000], 5000, 1)

        self.assertGreaterEqual(particlefilter.tag_position[0], 10000 - max_error)
        self.assertLessEqual(particlefilter.tag_position[0], 10000 + max_error)

        self.assertGreaterEqual(particlefilter.tag_position[1], 15000 - max_error)
        self.assertLessEqual(particlefilter.tag_position[1], 15000 + max_error)

        self.assertGreaterEqual(particlefilter.tag_position[2], 7000 - max_error)
        self.assertLessEqual(particlefilter.tag_position[2], 7000 + max_error)

        self.assertGreaterEqual(particlefilter.particle_quality, 0.95)


if __name__ == "__main__":
    unittest.main()
