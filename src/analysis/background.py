import collections
import ipc
import numpy
from numpy import abs
from backend import Backend

class MeanPhotonMap:
    def __init__(self, key, conf):
        xmin, xmax = conf["paramXmin"],  conf["paramXmax"]
        ymin, ymax = conf["paramYmin"],  conf["paramYmax"]
        xstep, ystep = conf["paramXstep"], conf["paramYstep"]
        self.photonMapX = numpy.linspace(xmin, xmax, (xmax-xmin)/float(xstep) + 1)
        self.photonMapY = numpy.linspace(ymin, ymax, (ymax-ymin)/float(ystep) + 1)
        self.photonMap  = numpy.zeros((self.photonMapY.shape[0], self.photonMapX.shape[0]), dtype=numpy.float)
        self.eventMap   = numpy.zeros((self.photonMapY.shape[0], self.photonMapX.shape[0]), dtype=numpy.float)
        self.meanMap    = numpy.zeros((self.photonMapY.shape[0], self.photonMapX.shape[0]), dtype=numpy.float)
        self.counter    = 0 
        ipc.broadcast.init_data(key, data_type='image', xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, xlabel=conf["xlabel"], ylabel=conf["ylabel"])

    def append(self, N, X, Y, G):
        self.photonMap[abs(self.photonMapY - Y.data).argmin(), abs(self.photonMapX - X.data).argmin()] += N
        self.eventMap[abs(self.photonMapY - Y.data).argmin(), abs(self.photonMapX - X.data).argmin()] += G
        visited = self.eventMap != 0
        self.meanMap[visited] = self.photonMap[visited] / self.eventMap[visited]
        #self.meanMap[~visited] = 1.1 * self.meanMap[visited].max()
        self.meanMap[~visited] = 0.0
        self.counter += 1

photonMaps = {}
def plotMeanPhotonMap(key, conf, nrPhotons, paramX, paramY, pulseEnergy):
    if not key in photonMaps:
        photonMaps[key] = MeanPhotonMap('meanPhotonMap_%s' %key,conf)
    m = photonMaps[key]
    m.append(nrPhotons, paramX, paramY, pulseEnergy)
    if(not m.counter % conf["updateRate"]):
        ipc.new_data('meanPhotonMap_%s' %key, m.meanMap)
    minimum = m.meanMap.min()
    #print minimum
    yopt, xopt = numpy.where(m.meanMap == minimum)
    #print yopt, xopt
    print "Current aperture position for %s: x=%d, y=%d" %(key, paramX.data, paramY.data)
    #print "Best position for %s: x=%.2f, y=%.2f, mean=%.2f" %(key, m.photonMapX[xopt[0]], m.photonMapY[yopt[0]], minimum)

def plotAperturePos(pos):
    ipc.new_data(pos.name, pos.data)
