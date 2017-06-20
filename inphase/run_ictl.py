#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import signal

from inphase import Experiment
from inphase.measurementprovider import *



def handler(signum, frame):
    global running, provider
    print('Signal handler called with signal', signum)
    running = False
    provider.close()


running = True
mytarget = 0xdb98
# provider = InphasectlMeasurementProvider('/dev/ttyUSB0', count=6, target=mytarget)
bridge_provider = InphasectlMeasurementProvider(address='localhost', count=6, target=mytarget)
provider = bridge_provider
signal.signal(signal.SIGINT, handler)

all_measurements = list()

# while running:
for x in range(3):
    measurements = provider.getMeasurements()
    all_measurements += measurements
    print("(%d/%d) target %x got %s measurements. Successful %d of %d" % (x+1, 3, mytarget, len(measurements), len(all_measurements), (x+1)*6))
    print("sleep 2 seconds")
    time.sleep(2)

provider.close()
