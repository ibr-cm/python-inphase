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
provider = InphasectlMeasurementProvider('/dev/ttyUSB0', count=6, target=mytarget)
signal.signal(signal.SIGINT, handler)

while running:
    measurements = provider.getMeasurements()
    print("target %x got %s measurements" % (mytarget, len(measurements)))
    print("sleep a second")
    time.sleep(1)
