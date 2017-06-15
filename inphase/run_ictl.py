#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from inphase import Experiment
from inphase.measurementprovider import *

import time

provider = InphasectlMeasurementProvider('/dev/ttyUSB0')

while True:
    measurements = provider.getMeasurements()
    print("got %s" % len(measurements))
    print("sleep")
    time.sleep(3)
