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
world = (-2000, 1000, -250, 1500, 700, 0)


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

    def __init__(self, world: World):
        # initialize the particle with a random position in the bounds of the given world
        x = np.random.uniform(world.dimensions_min[0], world.dimensions_max[0])
        y = np.random.uniform(world.dimensions_min[1], world.dimensions_max[1])
        z = np.random.uniform(world.dimensions_min[2], world.dimensions_max[2])
        self.position = np.array((x, y, z))
        self.world = world

        self.weight = 0.5

    def reweight(self, anchor_position, distance, sigma):
        # calculate the distance between current particle position and anchor
        dist = np.linalg.norm(anchor_position - self.position)
        # calculate the weight based on the difference between the measured distance
        # and the current distance of the particle from the anchor
        self.weight = scipy.stats.norm.pdf(distance, loc=dist, scale=sigma)

    def setPosition(self, x, y, z):
        self.position[0] = float(x)
        self.position[1] = float(y)
        self.position[2] = float(z)

    def move(self, sigma):
        # the particle moves a bit randomly
        self.position += np.random.normal(loc=sigma, size=3)

        # make sure it does not leave the world
        self.position = np.minimum(self.position, self.world.dimensions_max)
        self.position = np.maximum(self.position, self.world.dimensions_min)

    def copy(self):
        p = Particle(self.world)
        p.setPosition(self.position[0], self.position[1], self.position[2])
        return p

    def __repr__(self):
        return '[x=%.1f, y=%.1f, z=%.1f, w=%.5f]' % (self.position[0], self.position[1], self.position[2], self.weight)


class ParticleFilter:

    def __init__(self, world, particle_count=5000, sigma_prediction=5, sigma_mesasurement=300):
        self.world = world
        self.particle_count = particle_count
        self.sigma_prediction = sigma_prediction
        self.sigma_mesasurement = sigma_mesasurement

        # initialize particles
        self.particles = list()
        for i in range(self.particle_count):
            p = Particle(world)
            self.particles.append(p)

        self.tag_position = np.array((0.0, 0.0, 0.0))

    def resample(self, probabilities):
        """Resamples the particles

        Removes bad fitting particles and clones good particles for further runs
        """
        # draw particles based on their probabilities
        drawn = np.random.multinomial(self.particle_count, probabilities)  # each element of the array tells how often that index was drawn

        # create a new list of particles for the next iteration
        # reuse old particles if possible
        new_particles = list()
        for count, p in zip(drawn, self.particles):
            if count == 0:
                # do nothing as the particle is not needed anymore
                # it will die here
                continue
            else:
                new_particles.append(p)  # use particle again, it got drawn at least once
                for _ in range(1, count):  # this loop only iterates if count is > 1
                    # the particle got drawn multiple times
                    # it is duplicated
                    new_particles.append(p.copy())

        self.particles = new_particles

    def tick(self, anchor_pos, distance, dqf):
        weights = list()  # this holds the weights of all particles

        # process all particles
        for p in self.particles:

            ###################
            # prediction step #
            ###################

            # move the particle a bit
            p.move(self.sigma_prediction)

            ##################
            # weighting step #
            ##################

            # calculate the particle's weight
            p.reweight(anchor_pos, distance, self.sigma_mesasurement)
            # append to weight list
            weights.append(p.weight)

        # calculate probabities from weights (the sum must be 1.0)
        weights = np.array(weights)
        probabilities = weights / np.sum(weights)  # sum of weights is now 1

        # calculate the average tags position based on the particles and their probabilities
        new_tag_position = np.array((0.0, 0.0, 0.0))  # reset tag position
        for probability, p in zip(probabilities, self.particles):
            # new_tag_position += probability * p.position
            new_tag_position += p.position
        new_tag_position /= len(self.particles)
        self.tag_position = new_tag_position

        ###################
        # resampling step #
        ###################

        self.resample(probabilities)

        ###################
        # adaptation step #
        ###################

        # get the sum of the 100 best fitting particle's probabilities
        particle_quality = np.sum(probabilities[np.argsort(probabilities)[-100:]])
        print(particle_quality)

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
