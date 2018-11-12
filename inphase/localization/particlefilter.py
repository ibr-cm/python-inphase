"""Particle filter.

This module provides a particle filter for localization.

"""

import numpy as np
import scipy

import time
import logging

logger = logging.getLogger(__name__)


class World:
    """World for localization

    A world is a cube. All localization must be done within this cube's volume.
    """

    def __init__(self, x_dim, y_dim, z_dim=(0, 0)):
        # minimum corner of the cube
        self.dimensions_min = np.array((x_dim[0], y_dim[0], z_dim[0]))
        # maximum corner of the cube
        self.dimensions_max = np.array((x_dim[1], y_dim[1], z_dim[1]))


class ParticleFilter:
    """ A particle filter filter implementation

    It uses particles to find the position of a tag in 3D space.

    Each particle represents a possible position for the tag to be localized.
    Each particle has a weight (likeliness) to be in the correct position.
    Particles are moved around to find better positions.
    """

    def __init__(self, world, particle_count=5000, sigma_prediction=5, sigma_mesasurement=300, dimensions=3):
        self.world = world
        self.particle_count = particle_count
        self.sigma_prediction = sigma_prediction
        self.sigma_mesasurement = sigma_mesasurement
        self.dimensions = dimensions

        if self.dimensions == 2:
            self.world.dimensions_min[2] = 0
            self.world.dimensions_max[2] = 0

        # initialize particles
        self.positions = np.zeros((self.particle_count, 3))  # holds the positions of all particles
        self.weights = np.ones(self.particle_count) / self.particle_count  # holds the weights of all particles
        self.last_timestamp = time.time()
        self.randomizeParticles()

        self.tag_position = np.zeros(3)
        self.movement_vector = np.zeros(3)
        self.particle_quality = 0

        self.anchors = dict()

    def __str__(self):
        return "(%.0f, %.0f, %.0f) q=%.3f" % (self.tag_position[0], self.tag_position[1], self.tag_position[2], self.particle_quality)

    def randomizeParticles(self, stratified=True):
        """Puts particles into random positions on the map to restart the algorithm
        """
        if not stratified:
            # generate totally random particle positions
            self.positions = np.random.uniform(self.world.dimensions_min, self.world.dimensions_max, (self.particle_count, 3))

            # reset weights
            self.weights = np.ones(self.particle_count) / self.particle_count

            # set the last time the particles moved
            self.last_timestamp = time.time()

            return

        # generate stratified particle positions (stratified sampling)

        # volume/area of the world
        x_range = self.world.dimensions_max[0] - self.world.dimensions_min[0]
        y_range = self.world.dimensions_max[1] - self.world.dimensions_min[1]
        z_range = self.world.dimensions_max[2] - self.world.dimensions_min[2]
        volume = x_range * y_range
        if self.dimensions == 3:
            volume *= z_range

        # divide volume/area into one box/square per particle
        volume /= self.particle_count

        # get side length of the volume/area
        length = volume ** (1 / self.dimensions)

        # number of particles placed along each axis
        spaces_x = int(x_range / length)
        spaces_y = int(y_range / length)
        spaces_z = int(z_range / length)

        # number of particles placed on grid
        particles = spaces_x * spaces_y * spaces_z

        # number of particles to place randomly to get to correct amount of particles
        place_randomly = self.particle_count - particles

        # x y z coordinates of grid positions
        x_coordinates = np.linspace(self.world.dimensions_min[0], self.world.dimensions_max[0], spaces_x, endpoint=False)
        y_coordinates = np.linspace(self.world.dimensions_min[1], self.world.dimensions_max[1], spaces_y, endpoint=False)
        z_coordinates = np.linspace(self.world.dimensions_min[2], self.world.dimensions_max[2], spaces_z, endpoint=False)

        # array with all particle positions on the grid
        positions = np.array(np.meshgrid(x_coordinates, y_coordinates, z_coordinates)).T.reshape(-1, 3)

        # add some randomness to the position in the range [0, length]
        positions += np.random.uniform(0, length, (particles, 3))

        # create positions for the other particles that are positioned randomly
        random_positions = np.random.uniform(self.world.dimensions_min, self.world.dimensions_max, (place_randomly, 3))

        # concatenate grid placed and randomly placed particles
        self.positions = np.concatenate((positions, random_positions), axis=0)

        # reset weights
        self.weights = np.ones(self.particle_count) / self.particle_count

        # set the last time the particles moved
        self.last_timestamp = time.time()

    def predict(self, delta):
        """Moves particles around

        Particles move randomly so they can find better fitting positions
        """
        # MOVE!
        if delta is None:
            self.positions += np.random.normal(scale=self.sigma_prediction, size=(self.particle_count, 3))
        else:
            movement = delta * self.sigma_prediction
            if movement > 0:
                # only move if enough time passed so the particles can actually move
                movement_vectors = np.random.normal(scale=movement, size=(self.particle_count, 3))
                self.positions += movement_vectors

        # set third axis to 0 if run in 2D mode
        if self.dimensions == 2:
            self.positions[:, 2] = 0

    def weight(self, anchor_id, anchor_pos, distance, dqf):
        """Calculates the weights of the particles

        The weight is the metric that indicates how well the particle's position fits the measured distances.

        The sum of the weights is always 1, so they are also probabilities for the different particles.
        """
        # calculate the distance between current particle positions and anchor
        if len(anchor_pos) == 2:
            anchor_pos = np.array(anchor_pos + [0])  # add third dimension
        if self.dimensions == 2:
            anchor_pos[2] = 0
        vectors = self.positions - anchor_pos
        dists = np.linalg.norm(vectors, axis=1)
        # calculate the weight based on the difference between the measured distance
        # and the current distance of the particle from the anchor
        old_factor = (1 - dqf)
        self.weights *= old_factor
        self.weights += (1 - old_factor) * scipy.stats.norm.pdf(distance, loc=dists, scale=self.sigma_mesasurement)

        # set weight of particles outside of the map to 0
        # get all particles with position smaller than lower corner of map
        outside_low = np.any(np.less(self.positions, self.world.dimensions_min), axis=1)
        # get all particles with position greater than higher corner of map
        outside_high = np.any(np.greater(self.positions, self.world.dimensions_max), axis=1)

        # set the weights to 0 as the location cannot be there
        self.weights[outside_low] = 0
        self.weights[outside_high] = 0

        # normalize weights (the sum must be 1.0)
        self.weights /= np.sum(self.weights)  # sum of weights is now 1

    def localize(self, delta, fitting_fraction=0.1):
        """Calculates the average tags position based on the particles and their weights
        """

        #self.tag_position = np.dot(self.weights, self.positions)
        #self.tag_position = np.median(self.positions, 0)
        #self.tag_position = np.average(self.positions, 0)

        fitting_particles = int(self.particle_count * fitting_fraction)
        new_position = np.median(self.positions[np.argsort(self.weights)[-fitting_particles:]], 0)

        self.movement_vector = new_position - self.tag_position

        if delta is None:
            self.tag_position = new_position
        elif delta > 1:
            self.tag_position = new_position
        elif delta < 0:
            pass
        else:
            self.tag_position = (1 - delta) * self.tag_position + delta * new_position

        # get the sum of the best fitting particle's weights
        self.particle_quality = np.sum(self.weights[np.argsort(self.weights)[-fitting_particles:]]) / fitting_particles * self.particle_count

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
            logger.warning('Particle Filter needed hard reset!')
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
        logger.debug("new parameters: particle_count=%s, sigma_prediction=%s" % (self.particle_count, self.sigma_prediction))

    def tick(self, anchor_id, anchor_pos, distance, dqf, timestamp=None):
        if timestamp is None:
            delta = None
        else:
            delta = timestamp - self.last_timestamp
            self.last_timestamp = timestamp
        self.predict(delta)
        self.weight(anchor_id, anchor_pos, distance, dqf)
        self.resample()
        self.localize(delta)
        # do not do adaptation for now, it needs fine tuning
        # self.adapt()
