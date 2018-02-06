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
