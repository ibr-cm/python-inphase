"""Math functions.

This module contains math functions that are needed to work with InPhase measurement data.

"""

import numpy as np

from inphase.interpolation import parabolic
from inphase.constants import MAX_DISTANCE

DEFAULT_FFT_LEN = 4096


def calculateDistance(measurement, calc_type='complex', interpolation=None, **kwargs):
    """This function calculates a distance in millimeters a from :class:`Measurement` object.

    Args:
        measurement (:obj:`Measurement`): The measurement to calculate a distance for.
        calc_type (str, optional):  Algorithm to use for calculation:
        interpolation (string): Method of spectral interpolation, set value will be passed to interpolation function.

    `calc_type` can be one the following options:
            * `real` will use the algorithm published in our `INFOCOM paper`_
            * `complex` results in the more robust calculation via a complex valued FFT and allows double maximum distance, also allows usage of 'dc_threshold'

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
    extra_data = dict()

    fft_bins = kwargs.get('fft_bins', DEFAULT_FFT_LEN)
    dc_threshold = kwargs.get('dc_threshold', 0)

    fft_result, fft_extras = calc_fft_spectrum(measurement, calc_type, fft_bins)

    if calc_type == 'real':
        fft_length = fft_bins
    elif calc_type == 'complex':
        fft_length = len(fft_result)

    # search maxima
    # TODO implement multi maxima handling
    bin_pos = np.argmax(fft_result)
    bin_value = np.max(fft_result)

    if interpolation:
        bin_pos, bin_value = _interpolate_maxima_position(fft_result,
                                                          bin_pos,
                                                          mode=interpolation)

    if bin_pos < dc_threshold or bin_pos > fft_bins - dc_threshold:
        norm_bin_pos = np.nan
    else:
        # normalize bin position
        norm_bin_pos = _normalize_bin_pos(bin_pos, calc_type, fft_length)

    if np.isnan(norm_bin_pos):
        extra_data['dqi'] = 0
        distance = np.nan
    else:
        # store bin value as dqi
        extra_data['dqi'] = bin_value
        # calculate distance from bin position
        if calc_type == 'real':
            distance = _slopeToDist(norm_bin_pos)
        elif calc_type == 'complex':
            distance = _slopeToDist2(norm_bin_pos)

    # store extra data of FFT
    extra_data['fft'] = fft_result
    extra_data.update(fft_extras)

    # subtract antenna offsets if provided
    distance = substract_provided_offsets(measurement, distance)

    return distance, extra_data


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

    for sample in measurement['samples']:
        frequencies.append(sample['frequency'])
        pmu_values.append(sample['pmu_values'])

    # take mean of values as they might contain more than one pmu value per
    # frequency
    means = np.mean(pmu_values[:], 1)

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

    elif calc_type == 'complex':
        # map to 2*Pi
        means = means / 256.0 * 2 * np.pi

        complex_signal = np.cos(means) + 1j * np.sin(means)

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


def _normalize_bin_pos(bin_pos, calc_type, fft_bins=DEFAULT_FFT_LEN):
    """find bin with maximum peak and normalize to [0, 1]"""
    if calc_type == 'real':
        norm_bin_pos = bin_pos / float(fft_bins / 2.0)
    elif calc_type == 'complex':
        norm_bin_pos = bin_pos / fft_bins

    return norm_bin_pos


def substract_provided_offsets(measurement, distance):
    """Subtract antenna offsets from distance if provided in measurement"""

    if 'initiator' in measurement:
        if 'antenna_offset' in measurement['initiator']:
            distance -= measurement['initiator']['antenna_offset']

    if 'reflector' in measurement:
        if 'antenna_offset' in measurement['reflector']:
            distance -= measurement['reflector']['antenna_offset']

    return distance


def _slopeToDist(m, fd=0.5):
    # fd is the sample spacing in MHz
    c = 299792458                       # speed of light
    wavelength = c / (float(fd) * 10**6) * 0.5   # effective wavelength
    d_max = wavelength / 2                       # maximum distance with given frequency delta
    return d_max * m * 1000             # return value in millimeter


def _slopeToDist2(m, fd=0.5):
    # fd is the sample spacing in MHz
    c = 299792458                       # speed of light
    wavelength = c / (float(fd) * 10**6) * 0.5   # effective wavelength and maximum distance
    return wavelength * m * 1000                 # return value in millimeter
