#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import datetime
import os

import yaml


class Experiment:
    measurements = list()
    file_path = None

    def __init__(self, path):
        self.file_path = path

        # open the experiment file
        mode = 'r' if os.path.exists(path) else 'w+'
        with open(self.file_path, mode) as f:
            # read YAML data
            data = yaml.load(f.read())
        if not data:
            return
        if not isinstance(data, list):
            raise Exception('experiment file does not contain a list of measurements')

        for measurement in data:
            self.measurements.append(Measurement(measurement))

    def addMeasurement(self, measurement):
        # this adds the measurement and saves it to the disk (appends to file)
        self.measurements.append(measurement)

        # write to disk
        # make sure it writes pure yaml, no python objects
        with open(self.file_path, 'a') as f:
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
            f.write(yaml.dump([d]))


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
            except:
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


class UnitTest(unittest.TestCase):

    def helper_check_int_float(self, dictionary, entry, class_type):
        dictionary[entry] = 'string'
        with self.assertRaises(Exception):
            class_type(dictionary)

        dictionary[entry] = 15
        class_type(dictionary)

        dictionary[entry] = 15.5
        class_type(dictionary)

        del dictionary[entry]
        class_type(dictionary)

    def helper_check_list_int_float(self, dictionary, entry, class_type):
        dictionary[entry] = [-2, '2', 2, 3]
        with self.assertRaises(Exception):
            class_type(dictionary)

        dictionary[entry] = 'string'
        with self.assertRaises(Exception):
            class_type(dictionary)

    def setUp(self):
        self.sample_dict = {
            'frequency': 2435.5,
            'pmu_values': [-112, -100, 120, 0],
            'pmu_initiator': [49, 43, -10, 12],
            'pmu_reflector': [-95, -113, -126, 12],
            'rssi': [-70, -52, -60, -90]
        }

        self.node_dict = {
            'antenna_offset': 563.4,
            'location': [12000, 4000.5, None],
            'moving': False,
            'name': "Anchor 42",
            'uid': "1e:e3:f5:ff:fe:91:dc:3e"
        }

        self.measurement_dict = {
            'dqi': 86,
            'initiator': {
                'antenna_offset': 563.4,
                'location': [12000, 4000.5, None],
                'moving': False,
                'name': 'Anchor 42',
                'uid': '1e:e3:f5:ff:fe:91:dc:3e'
            },
            'measured_distance': 1230.5,
            'real_distance': 1200,
            'real_nlos': False,
            'reflector': {
                'antenna_offset': 563.4,
                'location': [15000, 8000, None],
                'moving': False,
                'name': 'Anchor 23',
                'uid': '1e:e3:f5:ff:fe:91:dc:4f'
            },
            'samples': [
                {
                    'frequency': 2435.5,
                    'pmu_initiator': [49, 43, -10, 12],
                    'pmu_reflector': [-95, -113, -126, 12],
                    'pmu_values': [-112, -100, 120, 0],
                    'rssi': [-70, -52, -60, -90]
                },
                {
                    'frequency': 2436,
                    'pmu_initiator': [49, 43, -10, 12],
                    'pmu_reflector': [-95, -113, -126, 12],
                    'pmu_values': [-112, -100, 120, 0],
                    'rssi': [-70, -52, -60, -90]
                },
                {
                    'frequency': 2436.5,
                    'pmu_initiator': [49, 43, -10, 12],
                    'pmu_reflector': [-95, -113, -126, 12],
                    'pmu_values': [-112, -100, 120, 0],
                    'rssi': [-70, -52, -60, -90]
                }
            ],
            'timestamp': 1481120002.23
        }

    def test_experiment(self):
        Experiment('testdata/measurement_data/experiment.yml')

        with self.assertRaises(Exception):
            Experiment('testdata/measurement_data/experiment_bad.yml')

    def test_experiment_new(self):
        e = Experiment('test.yml')
        e.addMeasurement(Measurement(self.measurement_dict))
        del e
        os.unlink('test.yml')

    def test_experiment_addMeasurement(self):
        # from: http://stackoverflow.com/questions/6587516/how-to-concisely-create-a-temporary-file-that-is-a-copy-of-another-file-in-pytho
        import tempfile
        import shutil

        def create_temporary_copy(path):
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, 'temp_file_name')
            shutil.copy2(path, temp_path)
            return temp_path

        path = create_temporary_copy('testdata/measurement_data/experiment.yml')

        e = Experiment(path)
        e.addMeasurement(Measurement(self.measurement_dict))
        e.addMeasurement(Measurement(self.measurement_dict))

        import filecmp
        self.assertTrue(filecmp.cmp(path, 'testdata/measurement_data/experiment_after_append.yml'))

        os.unlink(path)

    def test_measurement(self):
        m = Measurement(self.measurement_dict)
        self.assertIsInstance(m, Measurement)
        self.assertAlmostEqual(m['dqi'], 86)
        self.assertAlmostEqual(m['measured_distance'], 1230.5)
        self.assertAlmostEqual(m['real_distance'], 1200)
        self.assertFalse(m['real_nlos'])
        self.assertAlmostEqual(m['timestamp'], 1481120002.23)

    def test_measurement_timestamp(self):
        self.measurement_dict['timestamp'] = 'string'
        with self.assertRaises(Exception):
            Measurement(self.measurement_dict)

        del self.measurement_dict['timestamp']
        Measurement(self.measurement_dict)

    def test_measurement_initiator(self):
        self.measurement_dict['initiator'] = 'string'
        with self.assertRaises(Exception):
            Measurement(self.measurement_dict)

        del self.measurement_dict['initiator']
        Measurement(self.measurement_dict)

    def test_measurement_reflector(self):
        self.measurement_dict['reflector'] = 'string'
        with self.assertRaises(Exception):
            Measurement(self.measurement_dict)

        del self.measurement_dict['reflector']
        Measurement(self.measurement_dict)

    def test_measurement_samples(self):
        self.measurement_dict['samples'] = 'string'
        with self.assertRaises(Exception):
            Measurement(self.measurement_dict)

        del self.measurement_dict['samples']
        Measurement(self.measurement_dict)

    def test_measurement_dqi(self):
        self.helper_check_int_float(self.measurement_dict, 'dqi', Measurement)

    def test_measurement_measured_distance(self):
        self.helper_check_int_float(self.measurement_dict, 'measured_distance', Measurement)

    def test_measurement_real_distance(self):
        self.helper_check_int_float(self.measurement_dict, 'real_distance', Measurement)

    def test_measurement_real_nlos(self):
        self.measurement_dict['real_nlos'] = 'string'
        with self.assertRaises(Exception):
            Measurement(self.measurement_dict)

        self.measurement_dict['real_nlos'] = False
        Measurement(self.measurement_dict)

        self.measurement_dict['real_nlos'] = True
        Measurement(self.measurement_dict)

        del self.measurement_dict['real_nlos']
        Measurement(self.measurement_dict)

    def test_node(self):
        n = Node(self.node_dict)
        self.assertIsInstance(n, Node)
        self.assertAlmostEqual(n['antenna_offset'], 563.4)
        self.assertAlmostEqual(n['location'][0], 12000)
        self.assertAlmostEqual(n['location'][1], 4000.5)
        self.assertIsNone(n['location'][2])

    def test_node_moving(self):
        self.node_dict['moving'] = 'string'
        with self.assertRaises(Exception):
            Node(self.node_dict)

        self.node_dict['moving'] = False
        Node(self.node_dict)

        self.node_dict['moving'] = True
        Node(self.node_dict)

        del self.node_dict['moving']
        Node(self.node_dict)

    def test_node_location(self):
        self.node_dict['location'] = 'string'
        with self.assertRaises(Exception):
            Node(self.node_dict)

        self.node_dict['location'] = [0, 1, 2, 3]
        with self.assertRaises(Exception):
            Node(self.node_dict)

        self.node_dict['location'] = [0, 1, None]
        Node(self.node_dict)

        self.node_dict['location'] = [None, None, None]
        with self.assertRaises(Exception):
            Node(self.node_dict)

        self.node_dict['moving'] = True
        Node(self.node_dict)

        del self.node_dict['location']
        Node(self.node_dict)

    def test_node_antenna_offset(self):
        self.helper_check_int_float(self.node_dict, 'antenna_offset', Node)

    def test_sample(self):
        s = Sample(self.sample_dict)
        self.assertIsInstance(s, Sample)
        self.assertAlmostEqual(s['frequency'], 2435.5)
        self.assertEqual(len(s['pmu_values']), 4)
        self.assertEqual(len(s['pmu_initiator']), 4)
        self.assertEqual(len(s['pmu_reflector']), 4)
        self.assertEqual(len(s['rssi']), 4)

        self.helper_check_int_float(self.sample_dict, 'frequency', Sample)
        self.helper_check_list_int_float(self.sample_dict, 'pmu_values', Sample)
        self.helper_check_list_int_float(self.sample_dict, 'pmu_initiator', Sample)
        self.helper_check_list_int_float(self.sample_dict, 'pmu_reflector', Sample)
        self.helper_check_list_int_float(self.sample_dict, 'rssi', Sample)

if __name__ == "__main__":
    unittest.main()
