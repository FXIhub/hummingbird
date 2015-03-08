import collections
import ipc
import numpy
from numpy import abs
from backend import Backend
from plots import MeanMap

photonMaps = {}
def plotMeanPhotonMap(key, conf, nrPhotons, paramX, paramY, pulseEnergy):
    if not key in photonMaps:
        photonMaps[key] = MeanMap(key,conf)
    m = photonMaps[key]
    m.append(paramX, paramY, nrPhotons, pulseEnergy)
    if(not m.counter % conf["updateRate"]):
        m.update_center(paramX, paramY)
        m.update_local_limits()
        m.update_local_maps()
        m.update_gridmap(paramX,paramY)
        
        ipc.new_data(key+'overview', m.gridMap) 
        ipc.new_data(key+'local', m.localMeanMap, xmin=m.localXmin, xmax=m.localXmax, ymin=m.localYmin, ymax=m.localYmax)

    #minimum = m.meanMap.min()
    #print minimum
    #yopt, xopt = numpy.where(m.meanMap == minimum)
    #print yopt, xopt
    print "Current aperture position for %s: x=%d, y=%d" %(key, paramX.data, paramY.data)
    #print "Best position for %s: x=%.2f, y=%.2f, mean=%.2f" %(key, m.photonMapX[xopt[0]], m.photonMapY[yopt[0]], minimum)

def plotAperturePos(pos):
    ipc.new_data(pos.name, pos.data)
