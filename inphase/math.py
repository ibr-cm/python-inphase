"""Math functions.

This module contains math functions that are needed to work with InPhase measurement data.

"""

import numpy as np


def calculateDistance(measurement, calc_type='complex', **kwargs):
    """This function calculates a distance in millimeters a from :class:`Measurement` object.

    Args:
        measurement (:obj:`Measurement`): The measurement to calculate a distance for.
        calc_type (str, optional):  Algorithm to use for calculation:

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
    if calc_type is 'real':
        distance, extra_data['dqi'], extra_data['autocorrelation'], extra_data['fft'] = _calcDistReal(measurement, **kwargs)
    elif calc_type is 'complex':
        distance, extra_data['dqi'], extra_data['complex_signal'], extra_data['fft'] = _calcDistComplex(measurement, **kwargs)
    else:
        raise NotImplementedError('The chosen calc_type does not exist!')
    return distance, extra_data


def _calcDistReal(measurement, fft_bins=4096):
    """Calculates the distance via autocorrelation/fft from a given measurement"""

    # prepare lists for calculations
    frequencies = list()
    pmu_values = list()

    for sample in measurement['samples']:
        frequencies.append(sample['frequency'])
        pmu_values.append(sample['pmu_values'])

    # take mean of values as they might contain more than one pmu value per frequency
    means = np.mean(pmu_values[:], 1)

    # our definition of the autocorrelation function
    def autocorr(x):
        result = np.correlate(x, x, mode='full')
        return result[int(np.ceil(result.size/2)):]

    # autocorrelate
    autocorr_result = autocorr(means)

    # calculate fft
    fft_result = np.real(np.fft.fft(autocorr_result, fft_bins)[0:int(fft_bins/2)])

    # find bin with maximum peak and normalize to [0, 1]
    m = np.argmax(fft_result)/float(fft_bins/2.0)

    # calculate distance from bin position
    distance = _slopeToDist(m)
    dqi = np.max(fft_result)

    # subtract antenna offsets if provided
    if 'initiator' in measurement:
        if 'antenna_offset' in measurement['initiator']:
            distance -= measurement['initiator']['antenna_offset']

    if 'reflector' in measurement:
        if 'antenna_offset' in measurement['reflector']:
            distance -= measurement['reflector']['antenna_offset']

    return distance, dqi, autocorr_result, fft_result


def _slopeToDist(m, fd=0.5):
    # fd is the sample spacing in MHz
    c = 299792458                       # speed of light
    l = c / (float(fd) * 10**6) * 0.5   # effective wavelength
    d_max = l / 2                       # maximum distance with given frequency delta
    return d_max * m * 1000             # return value in millimeter


def _slopeToDist2(m, fd=0.5):
    # fd is the sample spacing in MHz
    c = 299792458                       # speed of light
    l = c / (float(fd) * 10**6) * 0.5   # effective wavelength and maximum distance
    return l * m * 1000                 # return value in millimeter


def _calcDistComplex(measurement, fft_bins=4096, dc_threshold=0):
    """Calculates the distance via complex signal/fft from a given measurement"""

    # prepare lists for calculations
    frequencies = list()
    pmu_values = list()

    for sample in measurement['samples']:
        frequencies.append(sample['frequency'])
        pmu_values.append(sample['pmu_values'])

    # take mean of values as they might contain more than one pmu value per frequency
    means = np.mean(pmu_values[:], 1)

    # map to 2*Pi
    means = means / 256.0 * 2 * np.pi

    complex_signal = np.cos(means) + 1j * np.sin(means)

    # calculate fft
    fft_result = np.absolute(np.fft.fft(complex_signal, fft_bins)[0:int(fft_bins)])

    if fft_bins % 2:
        # we have an odd number of bins
        # maximum positive and minimum negative frequency are aliases, remove the minumum negative frequency
        fft_result = np.delete(fft_result, int(fft_bins/2))

    # find bin with maximum peak and normalize to [0, 1]
    argmax = np.argmax(fft_result)
    if argmax < dc_threshold or argmax > fft_bins-dc_threshold:
        distance = np.nan
        dqi = 0
    else:
        m = argmax/len(fft_result)

        # calculate distance from bin position
        distance = _slopeToDist2(m)
        dqi = np.max(fft_result)

    # subtract antenna offsets if provided
    if 'initiator' in measurement:
        if 'antenna_offset' in measurement['initiator']:
            distance -= measurement['initiator']['antenna_offset']

    if 'reflector' in measurement:
        if 'antenna_offset' in measurement['reflector']:
            distance -= measurement['reflector']['antenna_offset']

    return distance, dqi, complex_signal, fft_result
