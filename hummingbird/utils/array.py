# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
import logging

import numpy


def slacH5ToCheetah(slacArr):
    out_arr = numpy.zeros((8*185, 4*388))
    for c in range(4):
        for r in range(8):
            slacPos = r + c*8
            (rB, rE) = (r*185, (r+1)*185)
            (cB, cE) = (c*388, (c+1)*388)
            out_arr[rB:rE, cB:cE] = (slacArr[slacPos])
    return out_arr


def cheetahToSlacH5(cheetahArr):
    out_arr = numpy.zeros((32, 185, 388))
    for c in range(4):
        for r in range(8):
            slacPos = r + c*8
            (rB, rE) = (r*185, (r+1)*185)
            (cB, cE) = (c*388, (c+1)*388)
            out_arr[slacPos] = cheetahArr[rB:rE, cB:cE]
    return out_arr

def assembleImage(x, y, img=None, nx=None, ny=None, dtype=None, return_indices=False):
    x -= x.min()
    y -= y.min()
    shape = (y.max() - y.min() + 1, x.max() - x.min() + 1)  
    (height, width) = shape
    if (nx is not None) and (nx > shape[1]):
        width = nx
    if (ny is not None) and (ny > shape[0]):
        height = ny 
    assembled = numpy.zeros((height,width))
    if return_indices:
        return assembled, height, width, shape, y, x
    assembled[height-shape[0]:, :shape[1]][y,x] = img
    if dtype is not None:
        assembled = assembled.astype(getattr(numpy, dtype))
    return assembled

def get2D(data):
    res = numpy.zeros(shape=(data.shape[0]*data.shape[2],data.shape[1]),dtype=data.dtype)
    for i in range(data.shape[2]):
        res[i*data.shape[0]:(i+1)*data.shape[0],:] = data[:,:,i]
    return res

def runningTrend(array, window, trend):
    nr_windows = (array.shape[0] / window)
    return trend(array[:nr_windows*window].reshape((window, nr_windows)), axis=0)

#def runningHistogram(array, window, bins, hmin, hmax):
#    nr_windows = (array.shape[0] / window)
#    buffer = array[:nr_windows*window].reshape((window, nr_windows))
#    runningHist = numpy.zeros((nr_windows, bins))
#    for i in range(nr_windows):
#        runningHist[i], bins = numpy.histogram(buffer[i], range=(hmin, hmax), bins=bins)
#    return runningHist

runningHist = {}
def runningHistogram(new_data, name, length=100, window=20, bins=100, hmin=0, hmax=100):
    if name not in runningHist:
        runningHist[name] = RunningHistogram(length=length, window=window, bins=bins, hmin=hmin, hmax=hmax)
    return runningHist[name].next(new_data, length=length, window=window, bins=bins, hmin=hmin, hmax=hmax)

class RunningHistogram:
    def __init__(self, length=100, window=20, bins=100, hmin=0, hmax=100):
        self.length = length
        self.window = window
        self.bins   = bins
        self.hmin   = hmin
        self.hmax   = hmax
        self.clear()

    def clear(self):
        self.buffer = numpy.zeros(shape=(self.window, self.bins))
        self.hist   = numpy.zeros(shape=(2*self.length, self.bins), dtype="int")
        self.i = 0

    def next(self, new_value, length=None, window=None, bins=None, hmin=None, hmax=None):
        reset = False
        for v in ["length", "window", "bins", "hmin", "hmax"]:
            exec("if self.%s != %s and %s is not None: reset = True" % (v,v,v))
            exec("if self.%s != %s and %s is not None: self.%s = %s" % (v,v,v,v,v))
        if reset:
            self.clear()
        # Update buffer
        i_bin = int(numpy.round((new_value - self.hmin)/float(self.hmax - self.hmin) * (self.bins-1)))
        if i_bin >= self.bins: 
            i_bin = self.bins-1
        if i_bin < 0:
            i_bin = 0
        i_buf = self.i % self.window
        self.buffer[i_buf, :]     = 0
        self.buffer[i_buf, i_bin] = 1
        # Update histogram
        i_his = self.i % self.length
        s = self.buffer.sum(0)
        self.hist[i_his, :]               = s[:]
        self.hist[i_his + self.length, :] = s[:]
        # Increase counter
        self.i += 1
        # Retrun slice
        sl = self.hist[i_his+1:self.length+i_his+1,:]
        return sl


def runningMean(x, N):
    """
    http://stackoverflow.com/questions/13728392/moving-average-or-running-mean
    """
    if x.shape[0] < N:
        return numpy.array([x.mean()])
    cumsum = numpy.cumsum(numpy.insert(x, 0, 0))
    return (cumsum[N:] - cumsum[:-N]) / float(N)
