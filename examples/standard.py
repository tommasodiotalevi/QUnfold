#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ---------------------- Metadata ----------------------
#
# File name:  standard.py
# Author:     Gianluca Bianco (biancogianluca9@gmail.com)
# Date:       2023-06-16
# Copyright:  (c) 2023 Gianluca Bianco under the MIT license.

# Data science modules
import numpy as np

# My modules
import sys

# Data generation modules
import ROOT as r

sys.path.append(".")
from studies.functions.generator import generate
from studies.functions.ROOT_converter import TH1_to_array, TH2_to_array

# QUnfold modules
from QUnfold import QUnfoldQUBO
from QUnfold import QUnfoldPlotter

# RooUnfold settings
loaded_RooUnfold = r.gSystem.Load("HEP_deps/RooUnfold/libRooUnfold.so")
if not loaded_RooUnfold == 0:
    sys.exit(0)


def main():

    # Generate data
    bins = 40
    min_bin = -10
    max_bin = 10
    truth, meas, response = generate("double-peaked", bins, min_bin, max_bin, 10000)
    truth = TH1_to_array(truth, overflow=True)
    meas = TH1_to_array(meas, overflow=True)
    response = TH2_to_array(response.Hresponse(), overflow=True)

    # Unfold with simulated annealing
    unfolder = QUnfoldQUBO(
        response,
        meas,
    )
    unfolder.solve_simulated_annealing(lam=0.1, num_reads=100)

    # Plot information
    plotter = QUnfoldPlotter(
        unfolder=unfolder, truth=truth, binning=np.linspace(min_bin, max_bin, bins + 1)
    )
    plotter.saveResponse("img/examples/standard/response.png")
    plotter.savePlot("img/examples/standard/comparison.png", "Simulated Annealing")


if __name__ == "__main__":
    main()
