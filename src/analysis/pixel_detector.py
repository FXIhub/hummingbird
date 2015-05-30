from numpy import sum, mean, min, max, std
import ipc
import numpy as np
from backend import ureg
from backend import Record
import utils.array

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

    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    central = []
    detector = evt[type][key]
    for i in range(4):
        central.append(detector.data[i*8+1,:,:194])
    evt["analysis"]["central4Asics"] = Record("central4Asics", np.hstack(central), detector.unit)
    
def totalNrPhotons(evt, type, key, aduPhoton=1, aduThreshold=0.5):
    """Estimates the total nr. of photons on the detector and adds it to ``evt["analysis"]["nrPhotons - " + key]``.

    Args:
        :evt:       The event variable
        :type(str): The event type (e.g. photonPixelDetectors)
        :key(str):  The event key (e.g. CCD)

    Kwargs:
        :aduPhoton(int):    ADU count per photon, default = 1
        :aduThreshold(int): only pixels above this threshold given in units of ADUs are valid, default = 0.5
    
    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    data  = evt[type][key].data.flat
    valid = data > aduThreshold
    evt["analysis"]["nrPhotons - " + key] = Record("nrPhotons - " + key , sum(data[valid]) / float(aduPhoton))

initialized = {}
def assemble(evt, type, key, x, y, nx=None, ny=None, outkey=None):
    """Assembles a detector image given some geometry and adds assembled image to ``evt["analysis"]["assembled - " + key]``.

    Args:
        :evt:        The event variable
        :type(str):  The event type (e.g. photonPixelDetectors)
        :key(str):   The event key (e.g. CCD)
        :x(int ndarray): X coordinates
        :y(int ndarray): Y coordinates

    Kwargs:
        :nx(int):    Total width of assembled image (zero padding)
        :ny(int):    Total height of assembled image (zero padding)

    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    if not key in initialized:
        assembled, height, width, shape, y, x = utils.array.assembleImage(x,y,nx=nx,ny=ny, return_indices=True)
        initialized[key] = {
            'assembled':assembled,
            'height':height,
            'width':width,
            'shape':shape,
            'y':y,
            'x':x
        }
    assembled = initialized[key]['assembled']
    height = initialized[key]['height']
    width = initialized[key]['width']
    shape = initialized[key]['shape']
    y = initialized[key]['y']
    x = initialized[key]['x']
    assembled[height-shape[0]:height, :shape[1]][y,x] = evt[type][key].data
    if outkey is None:
        evt["analysis"]["assembled - " + key] = Record("assembled - " + key, assembled)
    else:
        evt["analysis"][outkey] = Record(outkey, assembled)

    
