# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""A plotting module for correlations and maps"""
import numpy as np

from hummingbird import ipc
from hummingbird.backend import Record

histograms = {}
def plotHistogram(value, hmin=0, hmax=10, bins=10, name=None, group=None, buffer_length=100):
    if name is None:
        if hasattr(value, "name"):
            name = "Histogram of {0}".format(value.name)
        else:
            name = "Histogram"
    if (name not in histograms):
        ipc.broadcast.init_data(name, data_type='histogram', history_length=buffer_length,
                                hmin=hmin, hmax=hmax, bins=bins, group=group)
        histograms[name] = True
    value = value if not isinstance(value, Record) else value.data
    ipc.new_data(name, value, data_type="histogram")

normalized_histograms = {}
def plotNormalizedHistogram(value, weight, hmin=0, hmax=10, bins=10, name=None,
                          group=None, buffer_length=100):
    if name is None:
        if hasattr(value, "name"):
            name = "Normalized histogram of {0}".format(value.name)
        else:
            name = "Normalize histogram"
        
    if name not in normalized_histograms:
        ipc.broadcast.init_data(name, data_type='normalized_histogram', history_length=buffer_length,
                                hmin=hmin, hmax=hmax, bins=bins, group=group)
        normalized_histograms[name] = True
    value = value if not isinstance(value, Record) else value.data
    weight = weight if not isinstance(weight, Record) else weight.data
    ipc.new_data(name, np.array([value, weight]), data_type="normalized_histogram")
    #ipc.new_data(name, value)
