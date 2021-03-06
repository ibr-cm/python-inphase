import datetime
import os
import warnings

import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    warnings.warn("Using pure python yaml library, this might be very slow!", ImportWarning)
    from yaml import Loader, Dumper

import pickle  # for caching


class Experiment:

    def __init__(self, path, caching=True):
        self.file_path = path
        self.measurements = list()

        cache_path = path + '.cache'  # a possible caching file resides next to the original file

        cache_loaded = False

        # check if the experiment file exists
        if os.path.exists(path):
            # if it does, read it from disc
            mode = 'r'

            if caching:
                # caching is enabled, check if a cached file exists
                if os.path.exists(cache_path):
                    # a cache file exists, check if it is newer than the original yml
                    yaml_time = os.path.getmtime(path)
                    cache_time = os.path.getmtime(cache_path)
                    if yaml_time < cache_time:
                        # cache file is newer than yaml file, load cache file instead of yaml
                        with open(cache_path, 'rb') as f:
                            data = pickle.load(f)  # load data from pickled file instead of yaml
                        cache_loaded = True
        else:
            # if not, make a new empty file
            mode = 'w+'

        if not cache_loaded:
            # open the experiment yaml file
            with open(self.file_path, mode) as f:
                # read YAML data
                data = yaml.load(f, Loader=Loader)
        if not data:
            return
        if not isinstance(data, list):
            raise Exception('experiment file does not contain a list of measurements')

        for measurement in data:
            self.measurements.append(Measurement(measurement))

        if not cache_loaded:
            # if we made it until here, it means the cached file was not valid, save a new one if caching is requested
            if caching:
                with open(cache_path, 'wb') as f:
                    pickle.dump(data, f)

    def __iter__(self):
        return self.measurements.__iter__()

    def __len__(self):
        return self.measurements.__len__()

    def addMeasurements(self, measurements):
        # this adds the measurement and saves it to the disk (appends to file)
        self.measurements += measurements

        # write to disk
        # make sure it writes pure yaml, no python objects
        with open(self.file_path, 'a') as f:
            for measurement in measurements:
                d = dict(measurement)
                if 'initiator' in d:
                    d['initiator'] = dict(d['initiator'])
                if 'reflector' in d:
                    d['reflector'] = dict(d['reflector'])
                if 'samples' in d:
                    samples = list()
                    for s in d['samples']:
                        samples.append(dict(s))
                    d['samples'] = samples
                yaml.dump([d], f, Dumper=Dumper, default_flow_style=None)

    def addMeasurement(self, measurement):
        self.addMeasurements([measurement])


class Measurement(dict):
    def __init__(self, *arg, **kw):
        super(Measurement, self).__init__(*arg, **kw)

        if 'initiator' in self:
            if not isinstance(self['initiator'], dict):
                raise Exception('initiator is not a dict')
            self['initiator'] = Node(self['initiator'])
        if 'reflector' in self:
            if not isinstance(self['reflector'], dict):
                raise Exception('reflector is not a dict')
            self['reflector'] = Node(self['reflector'])

        if 'samples' in self:
            if not isinstance(self['samples'], list):
                raise Exception('samples are not a list')
            samples = list()
            for s in self['samples']:
                samples.append(Sample(s))
            self['samples'] = samples

        self.validate()

    def validate(self):
        # check if timestamp is a parsable unix timestamp (float)
        if 'timestamp' in self:
            try:
                datetime.datetime.fromtimestamp(self['timestamp'])
            except (TypeError, OverflowError, OSError):
                raise Exception('timestamp is not parsable')

        # initiator and reflector are checked in __init__

        # samples is checked in __init__

        # check if dqi is integer or float
        if 'dqi' in self:
            if not (isinstance(self['dqi'], int) or isinstance(self['dqi'], float)):
                raise Exception('dqi is neither integer nor float')

        if 'measured_distance' in self:
            if not (isinstance(self['measured_distance'], int) or isinstance(self['measured_distance'], float)):
                raise Exception('measured_distance is neither integer nor float')

        if 'real_distance' in self:
            if not (isinstance(self['real_distance'], int) or isinstance(self['real_distance'], float)):
                raise Exception('real_distance is neither integer nor float')

        if 'real_nlos' in self:
            if not isinstance(self['real_nlos'], bool):
                raise Exception('real_nlos is no boolean value')

        # TODO: check if status is valid


class Node(dict):
    def __init__(self, *arg, **kw):
        super(Node, self).__init__(*arg, **kw)
        self.validate()

    def validate(self):
        if 'moving' in self:
            if not isinstance(self['moving'], bool):
                raise Exception('real_nlos is no boolean value')

        if 'location' in self:
            if not isinstance(self['location'], list):
                raise Exception('location is not a list')
            if len(self['location']) != 3:
                raise Exception('location does not have three dimensions')

            for idx, axis in enumerate(self['location']):
                if 'moving' in self:
                    if self['moving']:
                        if axis is None:
                            continue
                if not (isinstance(axis, int) or isinstance(axis, float)):
                    if idx == 2:
                        if axis is None:
                            continue
                    raise Exception('location axis is neither integer nor float while the node is not moving')

        if 'antenna_offset' in self:
            if not (isinstance(self['antenna_offset'], int) or isinstance(self['antenna_offset'], float)):
                raise Exception('antenna_offset is neither integer nor float')


class Sample(dict):
    def __init__(self, *arg, **kw):
        super(Sample, self).__init__(*arg, **kw)
        self.validate()

    def _validate_list_int_float(self, key):
        if key in self:
            if not isinstance(self[key], list):
                raise Exception(key + ' is not a list')

            for idx, val in enumerate(self[key]):
                if not (isinstance(val, int) or isinstance(val, float)):
                    raise Exception(key + ' is neither integer nor float')

    def validate(self):
        if 'frequency' in self:
            if not (isinstance(self['frequency'], int) or isinstance(self['frequency'], float)):
                raise Exception('frequency is neither integer nor float')

        self._validate_list_int_float('pmu_values')
        self._validate_list_int_float('pmu_initiator')
        self._validate_list_int_float('pmu_reflector')
        self._validate_list_int_float('rssi')
