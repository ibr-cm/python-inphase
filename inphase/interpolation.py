#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parabolic Interpolation

This implementation is based on the
implementation in the waveform_analysis package from:

https://github.com/endolith/waveform_analysis

Modulo calculation is added to get around
access to out of bounds data. This is justified
as the spectrum is periodic."""


def parabolic(f, x):
    """
    Parabolic Interpolation for estimating the true maximum
    between to nearby samples.
    f is the spectrum and x is the estimated max (argmax)

    Returns (xv, yv) with the coordinates of the maximum
    of the calculated parabola.

    """
    a = (x-1) % len(f)
    c = (x+1) % len(f)
    xv = 1/2. * (f[a] - f[c]) / (f[a] - 2 * f[x] + f[c]) + x
    yv = f[x] - 1/4. * (f[a] - f[c]) * (xv - x)

    return (xv, yv)

