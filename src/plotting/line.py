"""A plotting module for line plots"""
import numpy as np
import ipc


histories = {}
def plotHistory(record, history=100):
    """Plotting history of record.data 

    Args:
        :record(Record): Record to be added to history and plotted

    Kwargs:
        :history(int):   Length of history buffer
    """
    plotid = "History(%s)" %record.name
    if (not record.name in histories):
        ipc.broadcast.init_data(plotid, history_length=history)
        histories[record.name] = True
    ipc.new_data(plotid, record.data)

histograms = {}
def plotHistogram(record, hmin=None, hmax=None, bins=100, history=100):
    """Plotting a histogram of record.data.flat
    
    Args:
        :record(Record):   Record to be histogrammed.

    Kwargs:
        :hmin(float):  Minimum, default = record.data.min()
        :hmax(float):  Maximum, default = record.data.max()
        :bins(int):    Nr. of bins, default = 100
        :history(int): Length of history buffer
    """
    plotid = "Histogram(%s)" %record.name
    if(not record.name in histograms):
        ipc.broadcast.init_data(plotid, data_type='vector', history_length=history)
        histograms[record.name] = True
    if hmin is None: hmin = record.data.min()
    if hmax is None: hmax = record.data.max()
    H,B = np.histogram(record.data.flat, range=(hmin, hmax), bins=bins)
    ipc.new_data(plotid, H, xmin=B.min(), xmax=B.max())


    
