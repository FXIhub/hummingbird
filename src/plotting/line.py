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
    if (not record.name in histories):
        ipc.broadcast.init_data(record.name, history_length=history)
        histories[record.name] = True
    ipc.new_data(record.name, record.data)

histograms = {}
def plotHistogram(record, hmin=0, hmax=100, bins=100, history=100):
    """Plotting a histogram of record.data.flat
    
    Args:
        :record(Record):   Record to be histogrammed.

    Kwargs:
        :hmin(float):  Minimum, default = 0
        :hmax(float):  Maximum, default = 100
        :bins(int):    Nr. of bins, default = 100
        :history(int): Length of history buffer
    """
    if(not record.name in histograms):
        ipc.broadcast.init_data(record.name, data_type='vector', history_length=history)
        histograms[record.name] = True
    H,B = numpy.histogram(record.data.flat, range=(hmin, hmax), bins=bins)
    ipc.new_data(record.name, H, xmin=B.min(), xmax=B.max())


    
