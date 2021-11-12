#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import inphase

import logging
import argparse
import matplotlib.pyplot as plt
import numpy as np

parser = argparse.ArgumentParser(description='Testbed Example')
parser.add_argument('experiment_filename', type=str,
                    help='experiment file to evaluate')
parser.add_argument('-l',  '--loglevel', type=str, default='ERROR',
                   help='level of debug output on console')

args = parser.parse_args()
# create logger
logger = logging.getLogger()
logger.setLevel(args.loglevel)

# create console handler and set level to debug
CON_HANDLER = logging.StreamHandler()
CON_HANDLER.setLevel(args.loglevel)

# create formatter
# TODO: use CONSTANT from inphase module
formatter = logging.Formatter('%(name)s/%(funcName)s (%(threadName)s) - %(levelname)s - %(message)s')

# add formatter to CON_HANDLER
CON_HANDLER.setFormatter(formatter)

# add CON_HANDLER to logger
logger.addHandler(CON_HANDLER)
logger = logging.getLogger(__name__)

experiment = inphase.Experiment(args.experiment_filename)

nodes = [{'hostname': 'socket://testbedpi-room112.ibr.cs.tu-bs.de:50000', 'node-address': 0xdc9f},
        {'hostname': 'socket://testbedpi-room116.ibr.cs.tu-bs.de:50000', 'node-address': 0x5a2e},
        {'hostname': 'socket://testbedpi-room118.ibr.cs.tu-bs.de:50000', 'node-address': 0x4eed},
        {'hostname': 'socket://testbedpi-room134.ibr.cs.tu-bs.de:50000', 'node-address': 0x3964}]

COUNT = 100

stats = dict()

for node in nodes:
    provider = inphase.measurementprovider.InphasectlMeasurementProvider(node['hostname'], count=COUNT, target=0x3964)
    stats[node['node-address']] = list()
    for target in filter(lambda target: target['node-address'] != node['node-address'], nodes):
        logger.info("Measuring initiator: 0x%x reflector 0x%x connection: %s" % (node['node-address'], target['node-address'], node['hostname']))
        provider.write_cfg(target=target['node-address'], count=COUNT)
        measurements = provider.getMeasurements()
        logger.info("Received %d of %d measurements." % (len(measurements), COUNT))
        stats[node['node-address']] += [{'target': target['node-address'], 'received': len(measurements), 'requested': COUNT}]
        experiment.addMeasurements(measurements)

    provider.close()
logger.info("Finished. Received %d of %d measurements." % (len(experiment.measurements), COUNT*len(nodes)*(len(nodes) - 1)))
import pprint
pp = pprint.PrettyPrinter(indent=4)
pp.pprint(stats)
