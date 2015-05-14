"""A plotting module for line plots"""
import numpy as np
import ipc


histories = {}
def plotHistory(param, history=100):
    """Plotting history of a parameter.

    Args:
        :param(Record):  The history is based on param.data

    Kwargs:
        :history(int):   Length of history buffer
    """
    plotid = "History(%s)" %param.name
    if (not param.name in histories):
        ipc.broadcast.init_data(plotid, history_length=history)
        histories[param.name] = True
    ipc.new_data(plotid, param.data)

histograms = {}
def plotHistogram(param, hmin=None, hmax=None, bins=100, history=100):
    """Plotting a histogram.
    
    Args:
        :param(Record):   The histogram is based on param.data.flat

    Kwargs:
        :hmin(float):  Minimum, default = record.data.min()
        :hmax(float):  Maximum, default = record.data.max()
        :bins(int):    Nr. of bins, default = 100
        :history(int): Length of history buffer
    """
    plotid = "Histogram(%s)" %param.name
    if(not param.name in histograms):
        ipc.broadcast.init_data(plotid, data_type='vector', history_length=history)
        histograms[param.name] = True
    if hmin is None: hmin = param.data.min()
    if hmax is None: hmax = param.data.max()
    H,B = np.histogram(param.data.flat, range=(hmin, hmax), bins=bins)
    ipc.new_data(plotid, H, xmin=B.min(), xmax=B.max())


    
