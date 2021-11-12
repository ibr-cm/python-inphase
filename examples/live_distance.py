#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import inphase

import time
import signal
import argparse

parser = argparse.ArgumentParser(description='Print measured distances to terminal.')
parser.add_argument('-p', '--port', type=str, default='/dev/ttyUSB0',
                    help='serial port to open')
parser.add_argument('-dc', '--dc_threshold', type=int, default=8,
                    help='amount of dc bins to set to NaN value')
parser.add_argument('-bins', '--fft_bins', type=int, default=4096,
                    help='amount of FFT output bins')
args = parser.parse_args()

if __name__ == "__main__":
    running = True

    def signal_handler(signal, frame):
        global running
        print('Exiting...')
        running = False

    signal.signal(signal.SIGINT, signal_handler)

    provider = inphase.SerialMeasurementProvider(args.port)

    while running:
        measurements = provider.getMeasurements()
        if measurements:
            for m in measurements:
                dist, extra_data = inphase.math.calculateDistance(m, fft_bins=args.fft_bins, dc_threshold=args.dc_threshold)
                print('Distance:', round(dist/1000, 2), 'm')
        time.sleep(0.1)

    provider.close()
