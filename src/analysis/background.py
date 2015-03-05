import collections
import ipc
import numpy
from numpy import abs
from backend import Backend


def plotMeanPhotonMap(nrPhotons, paramX, paramY):
    if(Backend.state['meanPhotonMap/initialize']):
        global photonMap, photonMapX, photonMapY, photonMapN
        xmin, xmax = Backend.state["meanPhotonMap/paramXmin"], Backend.state["meanPhotonMap/paramXmax"]
        ymin, ymax = Backend.state["meanPhotonMap/paramYmin"], Backend.state["meanPhotonMap/paramYmax"]
        xbin, ybin = Backend.state["meanPhotonMap/paramXbin"], Backend.state["meanPhotonMap/paramYbin"]
        photonMapX = numpy.linspace(xmin, xmax, (xmax-xmin)/float(xbin) + 1)
        photonMapY = numpy.linspace(ymin, ymax, (ymax-ymin)/float(ybin) + 1)
        photonMap = numpy.zeros((photonMapY.shape[0], photonMapX.shape[0]))
        photonMapN = 0
        Backend.state['meanPhotonMap/initialize'] = False
    photonMap[abs(photonMapY - paramY).argmin(), abs(photonMapX - paramX).argmin()] += nrPhotons
    photonMapN += 1
    if(not photonMapN % Backend.state["meanPhotonMap/updateRate"]):
        print photonMap.shape
        #print photonMap/float(photonMapN)
        print photonMap.sum(), float(photonMapN), (photonMap/float(photonMapN)).min(), (photonMap/float(photonMapN)).max()
        ipc.new_data('meanPhotonMap', photonMap/float(photonMapN))
