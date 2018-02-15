"""Particle filter.

This module provides a particle filter for localization.

"""

import numpy as np
import scipy

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


class Particle:
    """ A particle used by the particle filter

    Each particle represents a possible position for the tag to be localized.
    Particles can evaluate their likeliness to be in the correct position.
    Particles can move around (they move faster when their position is less likely).
    """

    def __init__(self, position, weight, world: World):
        # initialize the particles with a random position in the bounds of the given world
        self.position = position
        self.position[0] = np.random.uniform(world.dimensions_min[0], world.dimensions_max[0])
        self.position[1] = np.random.uniform(world.dimensions_min[1], world.dimensions_max[1])
        self.position[2] = np.random.uniform(world.dimensions_min[2], world.dimensions_max[2])
        self.world = world
        self.weight = weight

    def reweight(self, anchor_position, distance, sigma):
        # calculate the distance between current particle position and anchor
        dist = np.linalg.norm(anchor_position - self.position)
        # calculate the weight based on the difference between the measured distance
        # and the current distance of the particle from the anchor
        self.weight[0] = scipy.stats.norm.pdf(distance, loc=dist, scale=sigma)  # use array index to not overwrite the pointer with scalar value

    def setPosition(self, x, y, z):
        self.position[0] = float(x)
        self.position[1] = float(y)
        self.position[2] = float(z)

    def move(self, sigma):
        # the particle moves a bit randomly
        self.position[:] += np.random.normal(loc=sigma, size=3)

        # make sure it does not leave the world
        self.position[:] = np.minimum(self.position, self.world.dimensions_max)
        self.position[:] = np.maximum(self.position, self.world.dimensions_min)

    def __repr__(self):
        return '[x=%.1f, y=%.1f, z=%.1f, w=%.5f]' % (self.position[0], self.position[1], self.position[2], self.weight)


class ParticleFilter:

    def __init__(self, world, particle_count=5000, sigma_prediction=5, sigma_mesasurement=300):
        self.world = world
        self.particle_count = particle_count
        self.sigma_prediction = sigma_prediction
        self.sigma_mesasurement = sigma_mesasurement

        # initialize particles
        self.positions = np.zeros((particle_count, 3))  # holds the positions of all particles
        self.weights = np.zeros((particle_count, 1))    # holds the weights of all particles
        self.particles = list()                       # holds the particle objects themselves
        self.createParticles()

        self.tag_position = np.array((0.0, 0.0, 0.0))
        self.particle_quality = 0

    def createParticles(self):
        for i in range(self.particle_count):
            # this hands points to the full array
            p = Particle(self.positions[i], self.weights[i], self.world)
            self.particles.append(p)

    def resample(self, probabilities):
        """Resamples the particles

        Removes bad fitting particles and clones good particles for further runs
        """
        # draw particles based on their probabilities
        drawn = np.random.multinomial(self.particle_count, probabilities)  # each element of the array tells how often that index was drawn

        # make an array which contains the drawn positions the correct number of times
        new_positions = np.repeat(self.positions, drawn, 0)

        # set the particles positions to the new ones
        self.positions[:, :] = new_positions

    def tick(self, anchor_pos, distance, dqf):

        ###################
        # prediction step #
        ###################

        # move the particles a bit
        self.positions += np.random.normal(scale=self.sigma_prediction)

        ##################
        # weighting step #
        ##################

        # calculate the distance between current particle positions and anchor
        vectors = self.positions - anchor_pos
        dists = np.linalg.norm(vectors, axis=1)
        # calculate the weight based on the difference between the measured distance
        # and the current distance of the particle from the anchor
        self.weights[:, 0] = scipy.stats.norm.pdf(distance, loc=dists, scale=self.sigma_mesasurement)  # use array index to not overwrite the pointer with scalar value

        # calculate probabities from weights (the sum must be 1.0)
        probabilities = self.weights / np.sum(self.weights)  # sum of weights is now 1

        # calculate the average tags position based on the particles and their probabilities
        new_tag_position = np.array((0.0, 0.0, 0.0))  # reset tag position
        for probability, p in zip(probabilities, self.particles):
            new_tag_position += probability * p.position
            # new_tag_position += p.position
        # new_tag_position /= len(self.particles)
        self.tag_position = new_tag_position

        ###################
        # resampling step #
        ###################

        self.resample(probabilities[:, 0])

        ###################
        # adaptation step #
        ###################

        # get the sum of the 100 best fitting particle's probabilities
        self.particle_quality = np.sum(probabilities[np.argsort(probabilities)[-100:]]) / 100 * self.particle_count

        return  # do not do adaptation for now, it needs fine tuning

        if particle_quality > 0.2:
            self.sigma_prediction = 0.5
            self.particle_count = 1000
        elif particle_quality > 0.1:
            self.sigma_prediction = 5
            self.particle_count = 3000
        elif particle_quality > 0.05:
            self.sigma_prediction = 20
            self.particle_count = 5000
        elif particle_quality > 0.025:
            self.sigma_prediction = 50
            self.particle_count = 8000
        else:
            self.sigma_prediction = 100
            self.particle_count = 15000
        print("new parameters: particle_count=%s, sigma_prediction=%s" % (self.particle_count, self.sigma_prediction))
