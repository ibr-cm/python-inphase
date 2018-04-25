#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Slope-sampling based distance calculation.

This module contains other approaches to calculate the distance
from the phase data by using slope-sampling techniques.
"""

import numpy as np
from scipy.signal import savgol_filter
import peakutils.peak

from inphase.constants import SPEED_OF_LIGHT

from scipy.io import loadmat
import matplotlib.pyplot as plt


def prepare_pmu_samples(measurement):
    """Convert inphase measurement to phase data

    Args:
        measurement (:obj:`Measurement`): The measurement to calculate prepare.

    Returns:
        delta_phi: The phase values scaled to [0, 2pi]
        delta_f: The frequency offsets in Hz
        frequency_step: The difference between the first and the second frequency in Hz
    """
    pmu_data = np.array([(sample['frequency'], 127 + sample['pmu_values'][0]) for sample in measurement['samples']])

    # calculate frequency offsets and step
    delta_f = 10**6 * (pmu_data.T[0] - 2400)
    frequency_step = delta_f[1] - delta_f[0]
    # scale 8bit value to [0,2pi]
    delta_phi = 2*np.pi*1/256*pmu_data.T[1]

    return delta_phi, delta_f, frequency_step


def calc_dvss_spectrum(measurement, max_distance=30, resolution=3001, cut=None,
                       conf_rel=0, res_tol=1):
    d_samples = np.linspace(0, max_distance, resolution)
    delta_phi, delta_f, freq_step = prepare_pmu_samples(measurement)
    # plt.plot(delta_phi, label='delta phi from ideal pmu')
    # plt.legend()
    # plt.show()

    spectrum = dvss_spectrum(delta_phi, delta_f, freq_step, cut,
                             d_samples, conf_rel, res_tol)

    return spectrum


def calc_dist_via_slope_sampling(measurement, max_distance=30, resolution=3001, cut=None,
                                 conf_rel=0, res_tol=1):
    """Implementation of the distance via Slope Sampling Algorithm by Oshiga et al.

    The implementation is based on a port of the matlab code provided by the authors.
    The mathematical concepts and background are discribed in `OSHIGA paper`_

    Args:
        measurement (:obj:`Measurement`): The measurement to calculate a distance for.
        max_distance (float, optional): The highest distance which is expected. The default
                                        value is 30 m.
        resolution: (int, optional): The amount of samples between zero
        TODO: add these as kwargs?
        cut: (int, optional): Number of frequencies to include. If set to None all frequencies
                              are included.
        conf_rel: TODO
        res_tol: TODO

    Returns:
        * distances in meter (float)
        * dict with extra data from the distance calculation

    .. _OSHIGA paper:
        Efficient Slope Sampling Ranging and Trilateration Techniques for Wireless Localization
        TODO add url
    """

    d_samples = np.linspace(0, max_distance, resolution)
    delta_phi, delta_f, freq_step = prepare_pmu_samples(measurement)

    cdist, extra_data = slope_sampling(delta_phi, delta_f, freq_step, cut,
                                       d_samples, conf_rel, res_tol)

    return cdist, extra_data


def _calc_delta_phi(delta_phi, delta_f, df):
    """Calculate Delta Phi Matrix. (Equation 8)"""
    delta_phis = list()
    nr_comb = np.size(delta_phi, 0) # replace with len()
    nr_values = len(np.arange(0, max(delta_f) / df)) + 1
    for i in range(0, nr_comb):
        max_value = delta_f[i] / df
        values = np.arange(0, max_value)
        values = np.concatenate((values, [max_value]))
        values *= 2*np.pi
        values += delta_phi[i]
        new_values = values[-1] * np.ones(nr_values-len(values))
        # eq 8
        # append row
        delta_phis.append(np.concatenate((values, new_values)) / delta_f[i])

    return delta_phis, nr_comb


def _calc_sample_slopes(d_samples, wave_speed=SPEED_OF_LIGHT):
    """Calculate sample slopes (eq. 9)"""
    m_samples = (d_samples * 4 * np.pi) / wave_speed

    return m_samples


def _calc_A_B_matrices(nr_samples, nr_comb, delta_phis, m_samples):
    """Calculate matrix A (eq. 10) and matrix B (eq. 11)."""
    # index_res = np.array([(a, b) for a in range(0, nr_samples) for b in range(0, nr_comb)]).T

    print(nr_samples, nr_comb, np.array(delta_phis).shape, m_samples.shape)

    # eq 10
    # A_Delta = np.array(delta_phis)[index_res[1]]
    A_Delta = np.tile(np.array(delta_phis), (nr_samples, 1))

    # eq 11
    # B_sDelta = m_samples[index_res[0]]
    B_sDelta = np.repeat(m_samples, nr_comb)

    return A_Delta, B_sDelta


def _calc_residues(A_Delta, B_sDelta, m_samples, nr_comb):
    """Calculate residues between measured slopes and sample slopes."""
    # eq 12 inner
    residues = A_Delta.T - B_sDelta
    # eq 12 outer
    res_min = np.min(np.abs(residues), 0)
    # eq 13
    Rmin = np.reshape(res_min, (len(m_samples), nr_comb)).T

    return Rmin


def dvss_spectrum(delta_phi, delta_f, df, cut, d_samples, conf_rel, res_tol):
    delta_phis, nr_comb = _calc_delta_phi(delta_phi, delta_f, df)
    if cut:
        freq_include = round(cut * nr_comb / 100)
    else:
        freq_include = nr_comb-1  # all frequencies

    m_samples = _calc_sample_slopes(d_samples)

    A_Delta, B_sDelta = _calc_A_B_matrices(len(d_samples), nr_comb, delta_phis, m_samples)
    Rmin = _calc_residues(A_Delta, B_sDelta, m_samples, nr_comb)
    sort_res_min = np.sort(Rmin, 0)
    # eq 14
    res = np.median(sort_res_min[0:freq_include], 0)
    # frame_length = int(np.ceil(len(res)/10))
    # frame_length = 211
    # residues_filtered = savgol_filter(res, frame_length, 7)
    residues_filtered = res

    spectrum = 1/residues_filtered
    return spectrum


def slope_sampling(delta_phi, delta_f, df, cut, d_samples, conf_rel, res_tol):
    """Actual implementation of the dvss algorithm.
    TODO refactoring / pythonic rewrite recommended."""
    delta_phis, nr_comb = _calc_delta_phi(delta_phi, delta_f, df)
    # freq_include = freqInclude
    if cut:
        freq_include = round(cut * nr_comb / 100)
    else:
        freq_include = nr_comb-1  # all frequencies

    m_samples = _calc_sample_slopes(d_samples)

    ref_data = loadmat('DVSS1.mat')

    A_Delta, B_sDelta = _calc_A_B_matrices(len(d_samples), nr_comb, delta_phis, m_samples)
    Rmin = _calc_residues(A_Delta, B_sDelta, m_samples, nr_comb)

    print("Check res_min against ref_data: \t", np.allclose(Rmin, ref_data['res_min']))

    del ref_data
    ref_data = loadmat('DSS1b.mat')
    sort_res_min = np.sort(Rmin, 0)
    # eq 14
    res = np.median(sort_res_min[0:freq_include], 0)
    print("Check sort_res_min against ref_data: \t", np.allclose(sort_res_min, ref_data['sort_res_min']))
    print("Check res against ref_data: \t", np.allclose(res, ref_data['res_median']))
    frame_length = int(np.ceil(len(res)/10))
    frame_length = 211
    res_filt = savgol_filter(res, frame_length, 7)
    print("Check res_filt against ref_data: \t", np.allclose(res_filt, ref_data['res'][0]))
    plt.plot(res, '-o', label='res_median')
    plt.plot(res_filt, '-+', label='res_filt')
    plt.plot(ref_data['res_median'][0], '-s', label='ref_data res_median')
    plt.plot(ref_data['res'][0], '-s', label='ref_data res')
    plt.legend()
    # plt.show()
    # NOTE: workaround use filtered ref data
    # res_filt = ref_data['res'][0]
    plt.plot(res, label='res')
    plt.plot(res_filt, label='res_filt')
    plt.legend()
    plt.show()
    res = res_filt

    # Distance selection using Peak Search
    if res_tol == 0:
        res_tol = 1
    else:
        res_tol = (len(d_samples) - 1) / max(d_samples) * res_tol


    max_res = np.max(1/res)
    res_index = peakutils.peak.indexes(1/res, thres=0.3/max_res,
                                       min_dist=res_tol)
    conf_res = (1/res)[res_index]
    print("Check res_tol against ref_data: \t", float(ref_data['res_tol'][0][0]) == res_tol)


    plt.plot(1/res_filt, label='res_filt')
    plt.plot(1/ref_data['res'][0], '-s', label='ref_data res')
    plt.plot(res_index, conf_res, label='Found Peaks')
    import ipdb; ipdb.set_trace()
    ref_conf_res = 1/(ref_data['res'][0][ref_data['res_index']])
    plt.plot(ref_data['res_index'][0], ref_conf_res[0], label='ref Peaks')
    plt.legend()
    plt.show()

    print("Check res_index against ref_data: \t", np.allclose(res_index, ref_data['res_index'][0] - 1))

    # sort descending and return args
    res_index1 = np.argsort(conf_res)[::-1]
    conf_res = conf_res[res_index1]
    print("Check conf_res against ref_data: \t", np.allclose(conf_res, ref_data['conf_res'][0]))

    del ref_data
    ref_data = loadmat('DSSV1c.mat')
    a = 1
    i = 1
    while i <= len(conf_res) and a > conf_rel:
        d_conf = conf_res[0:i]/np.min(conf_res[0:i])
        d_conf_pre_norm = d_conf
        d_conf = d_conf/sum(d_conf)
        a = d_conf[-1]
        if a > conf_rel:
            # D = [d_samples[res_index(res_index1(1:i))]', res(res_index(res_index1(1:i)))', d_conf']
            distance = d_samples[res_index[res_index1[0:i]]].T
            residue = res[res_index[res_index1[0:i]]].T
            D = [distance, residue, d_conf.T]
        i = i + 1
    print("Check d_conf_pre_norm against ref_data: \t", np.allclose(d_conf_pre_norm, ref_data['d_conf_pre_norm'][0]))
    print("Check d_conf against ref_data: \t", np.allclose(d_conf, ref_data['d_conf'][0]))
    print("Check distance against ref_data: \t", np.allclose(distance, ref_data['D'].T[0]))
    print("Check residue against ref_data: \t", np.allclose(residue, ref_data['D'].T[1]))

    cdists = distance
    extra = {'dqi': np.max(d_conf),
             'dqis': np.array(d_conf),
             'd_samples': d_samples,
             'res': res,
             'D_res': residue}

    return cdists, extra
