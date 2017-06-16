import numpy as np


def calcDistFFT(measurement, fft_bins=4096):
    """Calculates the distance via autocorrelation/fft from a given measurement"""
    distance, dqi, autocorr_data, fft_data = calcDistFFTDetailed(measurement, fft_bins)
    return distance, dqi


def calcDistFFTDetailed(measurement, fft_bins=4096):
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


def calcDistComplexDetailed(measurement, fft_bins=4096):
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
    fft_result = np.absolute(np.fft.fft(complex_signal, fft_bins)[0:int(fft_bins/2)])

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

    return distance, dqi, complex_signal, fft_result
