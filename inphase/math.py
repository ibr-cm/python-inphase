#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Math functions.

This module contains math functions that are needed to work with InPhase
measurement data.

"""

from scipy.signal import argrelmax
import numpy as np

from inphase.interpolation import parabolic
from inphase.constants import SPEED_OF_LIGHT, DEFAULT_FREQ_SPACING

DEFAULT_FFT_LEN = 4096
DEFAULT_DC_TRESHOLD = 0
DEFAULT_MIN_REL_MAX = 0.2

def calculateDistance(measurement, calc_type='complex', interpolation=None, **kwargs):
    """This function calculates a distance in millimeters a from :class:`Measurement` object.

    Args:
        measurement (:obj:`Measurement`): The measurement to calculate a distance for.
        calc_type (str, optional):  Algorithm to use for calculation:
        `calc_type` can be one the following options:
                * `real` will use the algorithm published in our `INFOCOM paper`_
                * `complex` results in the more robust calculation via a complex valued FFT and allows double maximum distance.
        interpolation (string): Method of spectral interpolation, set value will be passed to interpolation function.

    Keyword Arguments:
        fft_bins (int): Number of FFT bins, more FFT bins result in higher resolution of the result.
        dc_threshold (int): Measurements around the **0** FFT bin are blocked and returned distance will be **None**.

    Returns:
        * distance in millimeter (float)
        * dict with extra data from the distance calculation

        Depending on the chosen `calc_type` the dict contains different extra information from the algorithms.

    .. _INFOCOM paper:
        https://www.ibr.cs.tu-bs.de/bib/xml/vonzengen:INFOCOM2016.html
    """
    distances, extra_data = calculateDistances(measurement, calc_type, interpolation, multi_max=False, **kwargs)

    # Take first = global maximum
    extra_data['dqi'] = extra_data['dqis'][0]
    #extra_data['multipath_dqi'] = _compute_multipath_dqi(extra_data['fft'])
    _compute_multipath_distance(extra_data, measurement, **kwargs)
    distance = distances[0]

    return distance, extra_data


def calculateDistances(measurement, calc_type='complex', interpolation=None, multi_max=True, **kwargs):
    extra_data = dict()
    maxima = list()

    fft_bins = kwargs.get('fft_bins', DEFAULT_FFT_LEN)
    dc_threshold = kwargs.get('dc_threshold', DEFAULT_DC_TRESHOLD)
    min_rel_max = kwargs.get('min_rel_max', DEFAULT_MIN_REL_MAX)

    fft_result, fft_extras = calc_fft_spectrum(measurement, calc_type, fft_bins)

    # search maxima
    if multi_max:
        for max_pos in argrelmax(fft_result)[0]:
            max_value = fft_result[max_pos]
            if max_value > min_rel_max:
                maximum = max_pos, max_value
                maxima.append(maximum)
    else:
        maximum = np.argmax(fft_result), np.max(fft_result)
        maxima.append(maximum)

    # import ipdb; ipdb.set_trace()
    distances = list()
    dqis = list()
    for idx, maximum in enumerate(maxima):
        bin_pos, bin_value = maximum
        # interpolate spectrum around maxima
        if interpolation:
            bin_pos, bin_value = _interpolate_maxima_position(fft_result,
                                                              bin_pos,
                                                              mode=interpolation)
            # update maximum with interpolation data
            maxima[idx] = bin_pos, bin_value

        if _in_dc_threshold(bin_pos, dc_threshold, fft_bins):
            # block positions around 0
            norm_bin_pos = np.nan
            dqi = 0
            distance = np.nan
        else:
            # normalize bin position
            fft_length = len(fft_result)
            norm_bin_pos = _normalize_bin_pos(bin_pos, fft_length)
            # store bin value as dqi
            dqi = bin_value
            # calculate distance from bin position
            if calc_type == 'real':
                # real fft calculation reduces d_max to the half
                distance = _slope_to_dist(norm_bin_pos, half_d_max=True)
            elif calc_type == 'complex':
                distance = _slope_to_dist(norm_bin_pos)
            elif calc_type == 'complex_with_magnitude':
                distance = _slope_to_dist(norm_bin_pos)

        # subtract antenna offsets if provided
        distance = substract_provided_offsets(measurement, distance)
        dqis.append(dqi)
        distances.append(distance)

    # store extra data of FFT
    extra_data['fft'] = fft_result
    extra_data.update(fft_extras)
    # store maxima in extra_data
    extra_data['maxima'] = maxima
    # store dqis in extra_data
    extra_data['dqis'] = dqis

    return distances, extra_data


def _compute_multipath_distance(extra_data, measurement, **kwargs):
    percent = kwargs.get('percent', 97)
    dqi_factor = kwargs.get('dqi_factor', 0.37)

    # this would be the original distance computation
    fft = extra_data['fft']
    pos = np.argmax(fft)
    dqi = fft[pos]

    fft_chopped = fft[:pos]
    relmax = argrelmax(fft_chopped)[0]
    values = fft_chopped[relmax]
    zipped = zip(relmax.tolist(), values.tolist())

    percentile = np.percentile(fft, percent)
    threshold = percentile + (dqi - percentile) * dqi_factor

    new_pos = None
    for relpos, reldqi in zipped:
        if reldqi > threshold:
            new_pos = relpos
            break

    if new_pos is not None:
        pos = new_pos

    extra_data['multipath_bin'] = pos
    pos, bin_value = _interpolate_maxima_position(fft, pos, mode='parabolic')

    dist = _slope_to_dist(pos / len(fft))
    dist = substract_provided_offsets(measurement, dist)

    extra_data['multipath_distance'] = dist

    # find the minimum left of the peak
    current_min = bin_value
    for i in reversed(range(extra_data['multipath_bin'])):
        if fft[i] > current_min:
            break
        current_min = fft[i]

    if extra_data['multipath_bin'] == 0:
        extra_data['multipath_dqi'] = 0
    else:
        extra_data['multipath_dqi'] = bin_value - np.max(fft[:i + 1])

    extra_data['multipath_percentile'] = threshold


def _compute_multipath_dqi(fft):
    pos = np.argmax(fft)
    dqi = fft[pos]

    #if pos == 0:
        # we cannot find another value...
    #    return 0.0

    #fft = fft[:pos]

    relmax = argrelmax(fft)[0]
    values = fft[relmax]

    zipped = list(zip(relmax.tolist(), values.tolist()))
    zipped.sort(key=lambda tup: tup[1], reverse=True)

    # largest value minus second largest value
    mpdqi = dqi * (dqi - zipped[1][1])

    return mpdqi


def _in_dc_threshold(bin_pos, dc_threshold, fft_bins):
    """Return whether a bin position is in [-dc_threshold, dc_threshold]"""
    return bin_pos < dc_threshold or bin_pos > fft_bins - dc_threshold


def _interpolate_maxima_position(fft, maximum, mode):
    """Use spectral interpolation to calculate better maximum position
       estimation."""
    if mode == 'parabolic':
        intp_m, intp_dqi = parabolic(fft, maximum)
    else:
        raise NotImplementedError('The chosen interpolation method does not exist!')

    return intp_m, intp_dqi


def calc_fft_spectrum(measurement, calc_type, fft_bins=DEFAULT_FFT_LEN):
    """Calculates the spectrum of the given measurement via selected fft type and
       length."""
    # prepare extra_data
    extra_data = dict()

    # prepare lists for calculations
    frequencies = list()
    pmu_values = list()
    rssi = list()

    for sample in measurement['samples']:
        frequencies.append(sample['frequency'])
        pmu_values.append(sample['pmu_values'])
        if 'rssi_remote' in sample:
            rssi.append(sample['rssi_remote'])

    # take mean of values as they might contain more than one pmu value per frequency
    # TODO: this is a bad idea, phase angles have to be averaged in the complex plane!
    means = np.mean(pmu_values[:], 1)

    # take mean of rssi samples
    if rssi:
        rssi = np.mean(rssi[:], 1)
        # convert rssi values to dBm according to the AT86RF233 datasheet
        rssi = -94 + 3 * rssi

        # convert dBm to milliwatt
        rssi = 10 ** (rssi / 10)

        extra_data['rssi'] = rssi

        # convert to voltage, impedance is 50 ohm
        voltage = np.sqrt(rssi * 50)
    else:
        voltage = None

    # use fft variant to calculate spectrum

    if calc_type == 'real':
        # our definition of the autocorrelation function
        def autocorr(x):
            result = np.correlate(x, x, mode='full')
            return result[int(np.ceil(result.size / 2)):]

        # autocorrelate
        autocorr_result = autocorr(means)

        # calculate fft
        # TODO check whether (fft_bins // 2) is sufficient to calculate range
        fft_result = np.real(np.fft.fft(autocorr_result, fft_bins)[0:int(fft_bins / 2)])

        # store intermidiate result as extra
        extra_data['autocorrelation'] = autocorr_result

    elif calc_type == 'complex_with_magnitude':
        # map to 2*Pi
        means = means / 256.0 * 2 * np.pi

        if voltage is None:
            raise Exception("You are trying to compute the distance with the \"complex_with_magnitude\" algorithm, but your measurement data does not contain RSSI values.")

        complex_signal = voltage * np.exp(1j * means)

        # calculate fft
        fft_result = np.absolute(np.fft.fft(complex_signal, fft_bins)[0:int(fft_bins)])

        # store intermidiate result as extra
        extra_data['complex_signal'] = complex_signal

        if fft_bins % 2:
            # we have an odd number of bins
            # maximum positive and minimum negative frequency are aliases,
            # remove the minumum negative frequency
            fft_result = np.delete(fft_result, int(fft_bins / 2))

    elif calc_type == 'complex':
        # map to 2*Pi
        means = means / 256.0 * 2 * np.pi

        #complex_signal = np.cos(means) + 1j * np.sin(means)
        complex_signal = 1 / len(means) * np.exp(1j * means)

        #window = np.hamming(len(means))
        #complex_signal *= window

        # calculate fft
        fft_result = np.absolute(np.fft.fft(complex_signal, fft_bins)[0:int(fft_bins)])

        # store intermidiate result as extra
        extra_data['complex_signal'] = complex_signal

        if fft_bins % 2:
            # we have an odd number of bins
            # maximum positive and minimum negative frequency are aliases,
            # remove the minumum negative frequency
            fft_result = np.delete(fft_result, int(fft_bins / 2))
    else:
        raise NotImplementedError('The chosen calc_type does not exist!')

    return fft_result, extra_data


def _normalize_bin_pos(bin_pos, fft_bins=DEFAULT_FFT_LEN):
    """find bin with maximum peak and normalize to [0, 1]"""
    return bin_pos / fft_bins


def substract_provided_offsets(measurement, distance):
    """Subtract antenna offsets from distance if provided in measurement"""

    if 'initiator' in measurement:
        if 'antenna_offset' in measurement['initiator']:
            distance -= measurement['initiator']['antenna_offset']

    if 'reflector' in measurement:
        if 'antenna_offset' in measurement['reflector']:
            distance -= measurement['reflector']['antenna_offset']

    if 'clock_drift_error' in measurement:
        distance -= measurement['clock_drift_error']

    return distance


def _slope_to_dist(m, fd=DEFAULT_FREQ_SPACING, half_d_max=False):
    """Calculate distance from slope of phase response.

    Args:
        m (float): The normalized bin position in [0, 1]
        fd (float, optional): fd is the sample spacing in MHz
        half_d_max (boolean, optional): If set true the maximum distance
                                        is halved

    Returns:
        * distance in millimeter (float)
    """
    c = SPEED_OF_LIGHT                          # speed of light c = 299792458 m/s
    wavelength = c / (float(fd) * 10**6) * 0.5  # effective wavelength in meter
    if half_d_max:
        d_max = wavelength / 2
    else:
        d_max = wavelength

    return d_max * m * 1000                     # return value in millimeter
