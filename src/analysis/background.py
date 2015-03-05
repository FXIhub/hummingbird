import collections
import ipc
import numpy
from numpy import abs
from backend import Backend

class MeanPhotonMap:
    def __init__(self, conf):
        #global photonMap, photonMapX, photonMapY, photonMapN
        xmin, xmax = conf["paramXmin"], conf["paramXmax"]
        ymin, ymax = conf["paramYmin"], conf["paramYmax"]
        xbin, ybin = conf["paramXbin"], conf["paramYbin"]
        self.photonMapX = numpy.linspace(xmin, xmax, (xmax-xmin)/float(xbin) + 1)
        self.photonMapY = numpy.linspace(ymin, ymax, (ymax-ymin)/float(ybin) + 1)
        self.photonMap = numpy.zeros((self.photonMapY.shape[0], self.photonMapX.shape[0]))
        self.photonMapN = 0

    def append(self, N, X, Y):
        self.photonMap[abs(self.photonMapY - Y.data).argmin(), abs(self.photonMapX - X.data).argmin()] += N
        self.photonMapN += 1

photonMaps = {}
def plotMeanPhotonMap(key, conf, nrPhotons, paramX, paramY):
    if not key in photonMaps:
        photonMaps[key] = MeanPhotonMap(conf)
    for k,m in photonMaps.iteritems():
        m.append(nrPhotons, paramX, paramY)
        if(not m.photonMapN % conf["updateRate"]):
            ipc.new_data('meanPhotonMap_%s_%s' %(paramX.name, paramY.name), m.photonMap/float(m.photonMapN))
