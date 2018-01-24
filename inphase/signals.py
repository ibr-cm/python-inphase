"""Signals

This module contains functions to generate intermediate signals
with defined shape.

"""
from numpy import linspace


def dist2slope(distance, fd=0.5):
    """This function """
    c = 299792458                       # speed of light
    wavelength = c / (float(fd) * 10**6) * 0.5   # effective wavelength and maximum distance

    return distance / 1000 / wavelength


def generate_sawtooth_samples(frequency, phase_shift=0, steps=200, frequency_inc=0.5, start_frequency=2400):
    """This function generates phase data.

    Args:
        frequency: Frequency of the phase data
        phase_shift: Shift of the phase data
        steps: Number of samples to calculate
        frequency_step: Increment of the frequency in each step
        start_frequency: Frequency to start

    Returns:
        samples (list): List of samples

    """

    sampling_points = linspace(0, frequency * 255, steps)
    sampling_points %= 255
    sampling_points -= 127

    counter = 0
    samples = list()
    for pmu_value in sampling_points:
        samples += [{'frequency': start_frequency + frequency_inc * counter,
                     'pmu_values': [int(pmu_value)]}]
        counter += 1
    return samples
