# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""A plotting module for correlations and maps"""
import ipc
from backend import Record

histograms = {}
def plotHistogram(value, hmin=0, hmax=10, bins=10, name=None, group=None, buffer_length=100):
    if name is None:
        name = "Histogram of {0}".format(value.name)
    if (name not in histograms):
        ipc.broadcast.init_data(name, data_type='histogram', history_length=buffer_length,
                                hmin=hmin, hmax=hmax, bins=bins, group=group)
        histograms[name] = True
    value = value if not isinstance(value, Record) else value.data
    ipc.new_data(name, value)
