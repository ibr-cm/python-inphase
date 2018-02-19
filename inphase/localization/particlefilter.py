"""Particle filter.

This module provides a particle filter for localization.

"""

import numpy as np
import scipy

import time

#############################
# Dimension of the used map #
#############################
# TU-night world
# world = (-2353, 4754, 2753, -1163)
# miklab world
# world = (0, 1100, 700, 0, 300, 0)
# Seatle
# world = (-2500, 1500, -750, 2200, 300, 0)
# hall
# world = (-2000, 1000, -250, 1500, 700, 0)


class World:
    """World for localization

    A world is a cube. All localization must be done within this cube's volume.
    """

    def __init__(self, x_dim: tuple, y_dim: tuple, z_dim: tuple):
        # minimum corner of the cube
        self.dimensions_min = np.array((x_dim[0], y_dim[0], z_dim[0]))
        # maximum corner of the cube
        self.dimensions_max = np.array((x_dim[1], y_dim[1], z_dim[1]))


class ParticleFilter:
    """ A particle filter filter implementation

    It uses particles to find the position of a tag in 3D space.

    Each particle represents a possible position for the tag to be localized.
    Each Particle has weight (likeliness) to be in the correct position.
    Particles are moved around to find better positions.
    """

    def __init__(self, world, particle_count=5000, sigma_prediction=5, sigma_mesasurement=300, weighting='classic', max_seconds=2):
        self.world = world
        self.particle_count = particle_count
        self.sigma_prediction = sigma_prediction
        self.sigma_mesasurement = sigma_mesasurement

        # initialize particles
        self.positions = np.zeros((self.particle_count, 3))  # holds the positions of all particles
        self.weights = np.zeros(self.particle_count)    # holds the weights of all particles
        self.randomizeParticles()

        self.tag_position = np.array((0.0, 0.0, 0.0))
        self.particle_quality = 0

        self.anchors = dict()

        self.anchor_position = None
        self.distance = None
        self.dqf = None

        self.max_seconds = max_seconds

        # choose weighting function
        if weighting == 'classic':
            self.weight = self.weight_classic
        elif weighting == 'multiple_anchors':
            self.weight = self.weight_multiple_anchors

    def __str__(self):
        return "(%.0f, %.0f, %.0f) q=%.3f" % (self.tag_position[0], self.tag_position[1], self.tag_position[2], self.particle_quality)

    def randomizeParticles(self):
        """Puts particles into random positions on the map to restart the algorithm
        """
        self.positions = np.random.uniform(self.world.dimensions_min, self.world.dimensions_max, (self.particle_count, 3))

    def predict(self):
        """Moves particles around

        Particles move randomly so they can find better fitting positions
        """
        # MOVE!
        self.positions += np.random.normal(scale=self.sigma_prediction, size=(self.particle_count, 3))

        # ensure all particles stay inside the map
        np.clip(self.positions, self.world.dimensions_min, self.world.dimensions_max, out=self.positions)

    def weight_classic(self):
        """Calculates the weights of the particles

        The weight is the metric that indicates how well the particle's position fits the measured distances.

        The sum of the weights is always 1, so they are also probabilities for the different particles.
        """
        # calculate the distance between current particle positions and anchor
        vectors = self.positions - self.anchor_position
        dists = np.linalg.norm(vectors, axis=1)
        # calculate the weight based on the difference between the measured distance
        # and the current distance of the particle from the anchor
        self.weights = scipy.stats.norm.pdf(self.distance, loc=dists, scale=self.sigma_mesasurement)

        # normalize weights (the sum must be 1.0)
        self.weights /= np.sum(self.weights)  # sum of weights is now 1

    def weight_multiple_anchors(self):
        """Calculates the weight of the particles based on multiple anchors

        """
        current_time = time.time()
        self.weights = np.zeros(self.particle_count)  # reset weights
        for key, anchor in self.anchors.items():
            # calculate the distance between current particle positions and anchor
            vectors = self.positions - anchor['position']
            dists = np.linalg.norm(vectors, axis=1)
            # calculate the weight based on the difference between the measured distance
            # and the current distance of the particle from the anchor
            distance_prob = scipy.stats.norm.pdf(anchor['distance'], loc=dists, scale=self.sigma_mesasurement)

            if self.max_seconds == 0:
                time_factor = 1
            else:
                self.max_seconds = 2
                delta = (current_time - anchor['time'])
                time_factor = -1 / self.max_seconds * delta
                time_factor = min(0, time_factor)

            dqf_factor = anchor['dqf']

            self.weights += distance_prob * time_factor * dqf_factor

        # normalize weights (the sum must be 1.0)
        self.weights /= np.sum(self.weights)  # sum of weights is now 1

    def localize(self):
        """Calculates the average tags position based on the particles and their weights
        """
        self.tag_position = np.dot(self.weights, self.positions)

        # get the sum of the 100 best fitting particle's weights
        self.particle_quality = np.sum(self.weights[np.argsort(self.weights)[-100:]]) / 100 * self.particle_count

    def resample(self):
        """Resamples the particles

        Removes bad fitting particles and clones good particles for further runs
        """
        # draw particles based on their probabilities
        drawn = np.random.multinomial(self.particle_count, self.weights)  # each element of the array tells how often that index was drawn

        # make an array which contains the drawn positions the correct number of times
        try:
            self.positions = np.repeat(self.positions, drawn, 0)
            self.weights = np.repeat(self.weights, drawn, 0)
        except ValueError:
            # the above line can fail if all particles are highly unlikely and none of them was drawn
            print('WARNING: Particle Filter needed hard reset!')
            self.randomizeParticles()

    def adapt(self):
        if self.particle_quality > 0.2:
            self.sigma_prediction = 0.5
            self.particle_count = 1000
        elif self.particle_quality > 0.1:
            self.sigma_prediction = 5
            self.particle_count = 3000
        elif self.particle_quality > 0.05:
            self.sigma_prediction = 20
            self.particle_count = 5000
        elif self.particle_quality > 0.025:
            self.sigma_prediction = 50
            self.particle_count = 8000
        else:
            self.sigma_prediction = 100
            self.particle_count = 15000
        print("new parameters: particle_count=%s, sigma_prediction=%s" % (self.particle_count, self.sigma_prediction))

    def addDistance(self, anchor_id, anchor_pos, distance, dqf):
        self.anchor_position = anchor_pos
        self.distance = distance
        self.dqf = dqf

        self.anchors[anchor_id] = {
            'position': anchor_pos,
            'distance': distance,
            'dqf': dqf,
            'time': time.time()
        }

    def tick(self):
        if not self.anchor_position:
            return
        self.predict()
        self.weight()
        self.localize()
        self.resample()
        # do not do adaptation for now, it needs fine tuning
        # self.adapt()
