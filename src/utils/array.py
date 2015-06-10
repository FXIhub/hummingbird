import numpy
import logging

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
    assembled[height-shape[0]:height, :shape[1]][y,x] = img
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

def runningHistogram(array, window, bins, hmin, hmax):
    nr_windows = (array.shape[0] / window)
    buffer = array[:nr_windows*window].reshape((window, nr_windows))
    runningHist = numpy.zeros((nr_windows, bins))
    for i in range(nr_windows):
        runningHist[i], bins = numpy.histogram(buffer[i], range=(hmin, hmax), bins=bins)
    return runningHist


runningHist = {}
def runningHistogram2(name, length, window, bins, hmin, hmax):
    if name is not in runningHist:
        runningHist[name] = {}
        runningHist[name][bnumpy.zeros(length-window, bins)
    nr_windows = (array.shape[0] / window)
    buffer = array[:nr_windows*window].reshape((window, nr_windows))
    runningHist = numpy.zeros((nr_windows, bins))
    for i in range(nr_windows):
        runningHist[i], bins = numpy.histogram(buffer[i], range=(hmin, hmax), bins=bins)
    return runningHist


def runningMean(x, N):
    """
    http://stackoverflow.com/questions/13728392/moving-average-or-running-mean
    """
    if x.shape[0] < N:
        return sum(x)
    cumsum = numpy.cumsum(numpy.insert(x, 0, 0))
    return (cumsum[N:] - cumsum[:-N]) / N
