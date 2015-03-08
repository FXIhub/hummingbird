from numpy import sum, mean, min, max, std
import ipc
import numpy
from backend import Backend

def printStatistics(detectors):
    for k,r in detectors.iteritems():
        v = r.data
        print "%s (%s): sum=%g mean=%g min=%g max=%g std=%g" % (k, r.unit.units,
                                                                sum(v), mean(v),
                                                                min(v), max(v),
                                                                std(v))
def plotImages(detectors):
    for k,r in detectors.iteritems():
        v = r.data
        if('squareImage' in Backend.state and Backend.state['squareImage']):
            ipc.new_data(k, v**2)
        else:
            ipc.new_data(k, v)

detectors = {}
def plotDetector(detector):
    if(not detector.name in detectors):
        ipc.broadcast.init_data(detector.name, data_type='image', history_length=10)
        detectors[detector.name] = 1
    sh = detector.data.shape
    if (detector.data.ndim == 3):
        image = detector.data.reshape(sh[0]*sh[2], sh[1])
    else:
        image = detector.data
    #if(not counter % Backend.state["detectorUpdateRate"]):
    ipc.new_data(detector.name, image)

def plotHistogram(key, detector, conf):
    hist, bins = numpy.histogram(detector.flat, range=(conf["hmin"], conf["hmax"]), bins=conf["nbins"])
    ipc.new_data(key, hist, xmin=bins.min(), xmax=bins.max())

def reshape_detector(detector):
    central = []
    for i in range(4):
        central.append(detector.data[i*8+1,:,:194])
    return numpy.hstack(central)
    
nrPhotons = {}    
def countNrPhotons(image):
    return sum(image[image>Backend.state['aduThreshold']]) / float(Backend.state['aduPhoton'])

def plotNrPhotons(key, nrPhotons):
    ipc.new_data(key, nrPhotons)

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
