from inphase import Sample
import numpy as np

import itertools


class MeasurementModifier:
    pass


class CutoffDecimator(MeasurementModifier):

    def __init__(self, count):
        self.count = count

    def modify(self, measurement):
        measurement['samples'] = measurement['samples'][0:self.count]


class PMUNoise(MeasurementModifier):
    def __init__(self, mu=0.7, sigma=25.7, samples=200):
        self.mu = mu
        self.sigma = sigma
        np.random.seed(17121986)
        self.pmu_noise = np.random.normal(mu, sigma, 200)

    def reset_noise_src(self):
        self.pmu_noise = np.random.normal(self.mu, self.sigma, 200)

    def add_noise_to_samples(self, samples):
        for sample, noise in zip(samples, self.pmu_noise):
            new_pmu_values = np.array([int(round(value + noise)) for value in sample['pmu_values']])
            new_pmu_values[new_pmu_values > 127] -= 256
            new_pmu_values[new_pmu_values < -128] += 256
            sample['pmu_values'] = [int(val) for val in new_pmu_values]

    def modify(self, m):
        self.reset_noise_src()
        self.add_noise_to_samples(m['samples'])


class MRLAInterpolator(MeasurementModifier):

    def __init__(self):
        pass

    def modify(self, measurement):
        new_samples = dict()
        start_freq = measurement['samples'][0]['frequency']

        # add start frequency sample
        new_samples[start_freq] = np.array(measurement['samples'][0]['pmu_values'])

        for a, b in itertools.combinations(measurement['samples'], 2):
            pmu_values = list()
            frequency = b['frequency'] - a['frequency'] + start_freq
            for va, vb in zip(a['pmu_values'], b['pmu_values']):
                v = vb - va
                if v > 127:
                    v -= 256
                elif v < -128:
                    v += 256
                pmu_values.append(v)

            if frequency in new_samples:
                new_samples[frequency] = np.append(new_samples[frequency], pmu_values)
            else:
                new_samples[frequency] = np.array(pmu_values)

        samples_list = list()

        # average the samples if we have multiple
        # beware: these are phase angles and have to be averaged via vectors in the complex space!
        for frequency, samples in new_samples.items():
            samples = samples / 128 * np.pi  # values now range from -Pi to Pi
            samples = np.cos(samples) + 1j * np.sin(samples)  # get complex vectors
            samples_sum = np.sum(samples)  # add complex vectors
            angle = np.angle(samples_sum)  # angle in radians
            pmu_value = angle / (2 * np.pi)  # bring to range [0,1]
            pmu_value *= 256  # bring to range [0,255]
            pmu_value -= 128  # bring to range [-128, 127]

            s = Sample({
                'frequency': frequency,
                'pmu_values': [pmu_value]
            })
            samples_list.append(s)

        # sort list
        samples_list = sorted(samples_list, key=lambda k: k['frequency'])

        measurement['samples'] = samples_list


class MRLADecimator(MeasurementModifier):

    def __init__(self):
        self.patterns = dict()
        self.patterns[199] = 'xxxxxoooxoooxooxooooooxoooooooooooooooxoooooooooooooooxoooooooooooooooxoooooooooooooooxoooooooooooooooxoooooooooooooooxoooooooooooooooxoooooooooooooooxoooooooooooooooxooooooooxooxooxooooooooxooxoxooox'

    def modify(self, measurement):
        new_samples = list()
        for s, ant in zip(measurement['samples'], self.patterns[199]):
            if ant == 'x':
                new_samples.append(s)
        measurement['samples'] = new_samples


class PMUSampleError(MeasurementModifier):

    """Replaces PMU samples with random data

    Attributes:
        count (int): number of samples to replace with random data
    """

    def __init__(self, count=100):
        self.count = count
        self.rng = np.random.default_rng(17121986)  # initialize random number generator with predictable randomness (seed)

    def add_error(self, samples):
        # create random data in range [-127, 128]
        random_data = self.rng.integers(-127, 128, size=self.count, endpoint=True)

        # spread random samples across the sample array
        nans = np.zeros(len(samples) - self.count)  # create zero array
        nans[:] = np.nan  # set everything to nan
        random_positions = np.concatenate((random_data, nans))  # join both arrays
        self.rng.shuffle(random_positions)  # shuffle the random positions

        for sample, random_value in zip(samples, random_positions):
            if not np.isnan(random_value):
                sample['pmu_values'] = [int(random_value) for val in sample['pmu_values']]  # replace all samples with the random value

    def modify(self, m):
        self.add_error(m['samples'])


class PMUBurstError(MeasurementModifier):

    """Replaces a block of samples with random data

    Attributes:
        length (int): Block length to replace
    """

    def __init__(self, length=100):
        self.length = length
        self.rng = np.random.default_rng(17121986)  # initialize random number generator with predictable randomness (seed)

    def add_error(self, samples):
        # create random data in range [-127, 128]
        random_data = self.rng.integers(-127, 128, size=self.length, endpoint=True)

        # generate offset where to place the random data
        offset = self.rng.integers(0, len(samples) - self.length, size=1, endpoint=True)[0]  # make sure the random_data always fits into the samples (no overlap at end)

        nans = np.zeros(offset)  # create zero array
        nans[:] = np.nan  # set everything to nan

        # add offset to beginning
        burst_error = np.concatenate((nans, random_data))

        nans = np.zeros(len(samples) - len(burst_error))  # create zero array
        nans[:] = np.nan  # set everything to nan

        # add nans to end
        burst_error = np.concatenate((burst_error, nans))

        for sample, random_value in zip(samples, burst_error):
            if not np.isnan(random_value):
                sample['pmu_values'] = [int(random_value) for val in sample['pmu_values']]  # replace all samples with the random value

    def modify(self, m):
        self.add_error(m['samples'])
