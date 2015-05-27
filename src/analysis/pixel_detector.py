from numpy import sum, mean, min, max, std
import ipc
import numpy as np
from backend import ureg
from backend import Record

def printStatistics(detectors):
    for k,r in detectors.iteritems():
        v = r.data
        print "%s (%s): sum=%g mean=%g min=%g max=%g std=%g" % (k, r.unit.units,
                                                                sum(v), mean(v),
                                                                min(v), max(v),
                                                                std(v))

def getCentral4Asics(evt, type, key):
    """Adds a one-dimensional stack of its 4 centermost asics
    to ``evt["analysis"]["central4Asics"]``.

    Args:
        :evt:       The event variable
        :type(str): The event type (e.g. photonPixelDetectors)
        :key(str):  The event key (e.g. CCD)
    """
    central = []
    detector = evt[type][key]
    for i in range(4):
        central.append(detector.data[i*8+1,:,:194])
    evt["analysis"]["central4Asics"] = Record("central4Asics", np.hstack(central), detector.unit)
    
nrPhotons = {}    
def totalNrPhotons(evt, type, key, aduPhoton=1, aduThreshold=0.5):
    """Estimates the total nr. of photons on the detector and adds it to ``evt["analysis"]["nrPhotons - " + key]``.

    Args:
        :evt:       The event variable
        :type(str): The event type (e.g. photonPixelDetectors)
        :key(str):  The event key (e.g. CCD)

    Kwargs:
        :aduPhoton(int):    ADU count per photon, default = 1
        :aduThreshold(int): only pixels above this threshold given in units of ADUs are valid, default = 0.5
    """
    detector = evt[type][key]
    data  = detector.data.flat
    valid = data > aduThreshold
    evt["analysis"]["nrPhotons - " + key] = Record("nrPhotons - " + key , sum(data[valid]) / float(aduPhoton))

"""
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
"""
