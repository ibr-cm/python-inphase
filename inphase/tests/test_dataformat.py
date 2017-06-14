#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from inphase import Experiment, Measurement, Sample, Node

import unittest
import os
THIS_DIR = os.path.dirname(os.path.abspath(__file__))


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
        e = Experiment(os.path.join(THIS_DIR, 'testdata/measurement_data/experiment.yml'))
        self.assertEqual(len(e.measurements), 2)

        e = Experiment(os.path.join(THIS_DIR, 'testdata/measurement_data/experiment.yml'))
        self.assertEqual(len(e.measurements), 2)

        with self.assertRaises(Exception):
            Experiment(os.path.join(THIS_DIR, 'testdata/measurement_data/experiment_bad.yml'))

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

        path = create_temporary_copy(os.path.join(THIS_DIR, 'testdata/measurement_data/experiment.yml'))

        e = Experiment(path)
        e.addMeasurement(Measurement(self.measurement_dict))
        e.addMeasurement(Measurement(self.measurement_dict))

        import filecmp
        self.assertTrue(filecmp.cmp(path, os.path.join(THIS_DIR, 'testdata/measurement_data/experiment_after_append.yml')))

        os.unlink(path)

    def test_experiment_addMeasurements(self):
        # from: http://stackoverflow.com/questions/6587516/how-to-concisely-create-a-temporary-file-that-is-a-copy-of-another-file-in-pytho
        import tempfile
        import shutil

        def create_temporary_copy(path):
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, 'temp_file_name')
            shutil.copy2(path, temp_path)
            return temp_path

        path = create_temporary_copy(os.path.join(THIS_DIR, 'testdata/measurement_data/experiment.yml'))

        e = Experiment(path)
        measurements = [Measurement(self.measurement_dict), Measurement(self.measurement_dict)]
        e.addMeasurements(measurements)

        import filecmp
        self.assertTrue(filecmp.cmp(path, os.path.join(THIS_DIR, 'testdata/measurement_data/experiment_after_append.yml')))

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
