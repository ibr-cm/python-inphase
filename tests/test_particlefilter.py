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

    def test_Particle(self):
        world = inphase.localization.particlefilter.World((-2000, 1000), (-250, 1500), (0, 700))

        # we have some randomness in particles so we have to test over a lot of them
        for i in range(10000):
            p = inphase.localization.particlefilter.Particle(np.zeros(3), np.zeros(1), world)

            # check if particle is inside world after initialization
            for pos, wmin, wmax in zip(p.position, world.dimensions_min, world.dimensions_max):
                self.assertGreaterEqual(pos, wmin)
                self.assertLessEqual(pos, wmax)

            # check if particle is inside world after move
            p.move(5)
            for pos, wmin, wmax in zip(p.position, world.dimensions_min, world.dimensions_max):
                self.assertGreaterEqual(pos, wmin)
                self.assertLessEqual(pos, wmax)

        # test setPosition
        p = inphase.localization.particlefilter.Particle(np.zeros(3), np.zeros(1),world)
        p.setPosition(1, 2, 3)
        self.assertEqual(p.position[0], 1)
        self.assertEqual(p.position[1], 2)
        self.assertEqual(p.position[2], 3)

        # test __repr__
        self.assertEqual(str(p), '[x=1.0, y=2.0, z=3.0, w=0.00000]')

        # test reweight
        sigma = 1
        anchor_position = np.array((1, 2, 3))  # anchor is in the same position as particle
        distance = 0
        p.reweight(anchor_position, distance, sigma)
        self.assertAlmostEqual(p.weight[0], 0.39894, 5)

        anchor_position = np.array((10, -10, 100))
        distance = 98.15  # anchor is ~98.15 units away from particle
        p.reweight(anchor_position, distance, sigma)
        self.assertAlmostEqual(p.weight[0], 0.39894, 5)

        distance = 95  # test with slightly wrong distance
        p.reweight(anchor_position, distance, sigma)
        self.assertAlmostEqual(p.weight[0], 0.002768, 5)

        distance = 5  # test with completely wrong distance
        p.reweight(anchor_position, distance, sigma)
        self.assertAlmostEqual(p.weight[0], 0.0, 5)

    def test_ParticleFilter(self):
        world = inphase.localization.particlefilter.World((-2000, 1000), (-250, 1500), (0, 700))
        particlefilter = inphase.localization.particlefilter.ParticleFilter(world)

        for _ in range(50):
            particlefilter.tick([500, 100, 200], 0, 1000)
            particlefilter.tick([100, 100, 200], 400, 1000)
            particlefilter.tick([500, 100, -300], 500, 1000)

        self.assertAlmostEqual(particlefilter.tag_position[0], 536.62901, 5)
        self.assertAlmostEqual(particlefilter.tag_position[1], 118.41677, 5)
        self.assertAlmostEqual(particlefilter.tag_position[2], 222.79566, 5)
        self.assertAlmostEqual(particlefilter.particle_quality, 1.01673, 5)


if __name__ == "__main__":
    unittest.main()
