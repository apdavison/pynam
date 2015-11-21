#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   PyNAM -- Python Neural Associative Memory Simulator and Evaluator
#   Copyright (C) 2015 Andreas Stöckel
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines

import math
import sys
import os

# Include the PyNAM folder
import __main__
sys.path.append(os.path.join(os.path.dirname(__main__.__file__), "../pynam"))

import binam
import data
import utils
import entropy

def cm2inch(value):
    return value / 2.54

# Parameters
n_bits = 96
n_ones = 8
n_samples = entropy.optimal_sample_count(n_bits_in = n_bits,
        n_bits_out = n_bits, n_ones_in=n_ones, n_ones_out = n_ones)

# Generate the input and output data
print("Create input data...")
X = data.generate(n_bits=n_bits, n_ones=n_ones, n_samples=n_samples)
print("Create output data...")
Y = data.generate(n_bits=n_bits, n_ones=n_ones, n_samples=n_samples)

# Train the BiNAM
print("Training BiNAM...")
M = binam.BiNAM(n_bits, n_bits)
M.train_matrix(X, Y)

print("Running experiments...")
xs = np.linspace(0.0, 1.0, 100)
nxs = len(xs)

info_p0_fix = np.zeros(nxs)
info_p1_fix = np.zeros(nxs)
info_p0_adap = np.zeros(nxs)
info_p1_adap = np.zeros(nxs)

fps_p0_fix = np.zeros((nxs, n_samples))
fps_p1_fix = np.zeros((nxs, n_samples))
fps_p0_adap = np.zeros((nxs, n_samples))
fps_p1_adap = np.zeros((nxs, n_samples))

fns_p0_fix = np.zeros((nxs, n_samples))
fns_p1_fix = np.zeros((nxs, n_samples))
fns_p0_adap = np.zeros((nxs, n_samples))
fns_p1_adap = np.zeros((nxs, n_samples))

i = 0
for p in xs:
    print("Iteration: ", p)

    # Introduce some errors
    X_part_p0 = np.minimum(X, (np.random.random((n_samples, n_bits)) >= p))
    X_part_p1 = np.maximum(X, (np.random.random((n_samples, n_bits)) < p))
    Y_part_out_p0_adap = M.evaluate_matrix(X_part_p0)
    Y_part_out_p1_adap = M.evaluate_matrix(X_part_p1)
    Y_part_out_p0_fix = M.evaluate_matrix(X_part_p0, threshold=n_ones)
    Y_part_out_p1_fix = M.evaluate_matrix(X_part_p1, threshold=n_ones)

    # Calculate the errors and the entropy
    errs = entropy.calculate_errs(Y_part_out_p0_adap, Y)
    info_p0_adap[i] = entropy.entropy_hetero(errs, n_bits_out=n_bits, n_ones_out=n_ones)
    fps_p0_adap[i] = np.array(map(lambda x: x["fp"], errs))
    fns_p0_adap[i] = np.array(map(lambda x: x["fn"], errs))

    errs = entropy.calculate_errs(Y_part_out_p1_adap, Y)
    info_p1_adap[i] = entropy.entropy_hetero(errs, n_bits_out=n_bits, n_ones_out=n_ones)
    fps_p1_adap[i] = np.array(map(lambda x: x["fp"], errs))
    fns_p1_adap[i] = np.array(map(lambda x: x["fn"], errs))

    errs = entropy.calculate_errs(Y_part_out_p0_fix, Y)
    info_p0_fix[i] = entropy.entropy_hetero(errs, n_bits_out=n_bits, n_ones_out=n_ones)
    fps_p0_fix[i] = np.array(map(lambda x: x["fp"], errs))
    fns_p0_fix[i] = np.array(map(lambda x: x["fn"], errs))

    errs = entropy.calculate_errs(Y_part_out_p1_fix, Y)
    info_p1_fix[i] = entropy.entropy_hetero(errs, n_bits_out=n_bits, n_ones_out=n_ones)
    fps_p1_fix[i] = np.array(map(lambda x: x["fp"], errs))
    fns_p1_fix[i] = np.array(map(lambda x: x["fn"], errs))

    i = i + 1

figsize = (cm2inch(12.8), cm2inch(6))

print("Plotting information...")
figInfo = plt.figure(figsize=figsize)
ax = figInfo.add_subplot(1, 1, 1)
ax.plot(xs, info_p0_adap, lw=0.75, color="k", label="Missing bits ($p_0$)")
ax.plot(xs, info_p1_adap, '--', lw=0.75, color="k", label="Additional bits ($p_1$)")
ax.plot(xs, info_p0_fix, lw=0.75, color="#3465a4")
ax.plot(xs, info_p1_fix, '--', lw=0.75, color="#3465a4")
ax.set_xlabel("Noise $p$")
ax.set_ylabel("Information [bits]")
ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.05), ncol=4)

figsize = (cm2inch(6), cm2inch(6))

print("Plotting false positives...")
figFP = plt.figure(figsize=figsize)
ax = figFP.add_subplot(1, 1, 1)
ax.plot(xs, np.mean(fps_p0_adap, 1), lw=0.75, color="k")
ax.plot(xs, np.mean(fps_p1_adap, 1), '--', lw=0.75, color="k")
ax.plot(xs, np.mean(fps_p0_fix, 1), lw=0.75, color="#3465a4")
ax.plot(xs, np.mean(fps_p1_fix, 1), '--', lw=0.75, color="#3465a4")
ax.set_xlabel("Noise $p$")
ax.set_ylabel("False positives [bits]")

print("Plotting false negatives...")
figFN = plt.figure(figsize=figsize)
ax = figFN.add_subplot(1, 1, 1)
ax.plot(xs, np.mean(fns_p0_adap, 1), lw=0.75, color="k")
ax.plot(xs, np.mean(fns_p1_adap, 1), '--', lw=0.75, color="k")
ax.plot(xs, np.mean(fns_p0_fix, 1), lw=0.75, color="#3465a4")
ax.plot(xs, np.mean(fns_p1_fix, 1), '--', lw=0.75, color="#3465a4")
ax.set_xlabel("Noise $p$")
ax.set_ylabel("False negatives [bits]")

figInfo.savefig("out/sketch_info_over_noise.pdf", format='pdf', bbox_inches='tight')
figFP.savefig("out/sketch_fps_over_noise.pdf", format='pdf', bbox_inches='tight')
figFN.savefig("out/sketch_fns_over_noise.pdf", format='pdf', bbox_inches='tight')

