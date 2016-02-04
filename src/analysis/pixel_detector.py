from backend import ureg
from backend import add_record
import utils.io
import utils.array
from numpy import sum, mean, min, max, std
import numpy as np

def printStatistics(detectors):
    for k,r in detectors.iteritems():
        v = r.data
        print "%s (%s): sum=%g mean=%g min=%g max=%g std=%g" % (k, r.unit.units,
                                                                sum(v), mean(v),
                                                                min(v), max(v),
                                                                std(v))

def getSubsetAsics(evt, type, key, subset, output):
    """Adds a one-dimensional stack of an arbitrary subset of asics
    to ``evt["analysis"][output]``.

    Args:
        :evt:       The event variable
        :type(str): The event type (e.g. photonPixelDetectors)
        :key(str):  The event key (e.g. CCD)
        :subset(list): Asic indices
        :output: The output key in analysis

    :Authors:
        Carl Nettelblad (carl.nettelblad@it.uu.se)
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    stack = []
    detector = evt[type][key]
    for i in subset:
        panel = i / 2
        asic = i % 2
        stack.append(detector.data[panel,:,(asic*194):((asic+1)*194)])
    add_record(evt["analysis"], "analysis", output, np.hstack(stack), detector.unit)

def getCentral4Asics(evt, type, key):
    """Adds a one-dimensional stack of its 4 centermost asics
    to ``evt["analysis"]["central4Asics"]``.

    Args:
        :evt:       The event variable
        :type(str): The event type (e.g. photonPixelDetectors)
        :key(str):  The event key (e.g. CCD)

    :Authors:
        Carl Nettelblad (carl.nettelblad@it.uu.se)
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    getSubsetAsics(evt, type, key, map(lambda i : (i * 8 + 1) * 2, xrange(4)), "central4Asics")

    
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
    add_record(evt["analysis"], "analysis", "nrPhotons - " + key, sum(data[valid]) / float(aduPhoton))

initialized = {}
def assemble(evt, type, key, x, y, nx=None, ny=None, subset=None, outkey=None):
    """Asesembles a detector image given some geometry and adds assembled image to ``evt["analysis"]["assembled - " + key]``.

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
        if subset is not None:
            x_ss = []
            y_ss = []
            for i in subset:
                panel = i / 2
                asic = i % 2
                x_ss.append(x[panel,:,(asic*194):((asic+1)*194)])
                y_ss.append(y[panel,:,(asic*194):((asic+1)*194)])
            x_ss = np.hstack(x_ss)
            y_ss = np.hstack(y_ss)
        else:
            x_ss = x
            y_ss = y
        assembled, height, width, shape, y_ss, x_ss = utils.array.assembleImage(x_ss, y_ss ,nx=nx, ny=ny, return_indices=True)
        initialized[key] = {
            'assembled':assembled,
            'height':height,
            'width':width,
            'shape':shape,
            'y':y_ss,
            'x':x_ss
        }
    assembled = initialized[key]['assembled']
    height = initialized[key]['height']
    width = initialized[key]['width']
    shape = initialized[key]['shape']
    y = initialized[key]['y']
    x = initialized[key]['x']
    if subset is not None:
        data = []
        for i in subset:
            panel = i / 2
            asic = i % 2
            data.append(evt[type][key].data[panel,:,(asic*194):((asic+1)*194)])
        data = np.hstack(data)
    else:
        data = evt[type][key].data
    assembled[height-shape[0]:, :shape[1]][y,x] = data
    if outkey is None:
        add_record(evt["analysis"], "analysis", "assembled - "+key, assembled)
    else:
        add_record(evt["analysis"], "analysis", outkey, assembled)

    
def bin(evt, type, key, binning, mask=None):
    """Bin a detector image given a binning factor (and mask).
    Adds the records ``evt["analysis"]["binned image - " + key]`` and  ``evt["analysis"]["binned mask - " + key]``.

    .. note:: This feature depends on the python package `libspimage <https://github.com/FilipeMaia/libspimage>`_.

    Args:
        :evt:        The event variable
        :type(str):  The event type (e.g. photonPixelDetectors)
        :key(str):   The event key (e.g. CCD)
        :binning(int):   The linear binning factor

    Kwargs:
        :mask:    Binary mask, pixels that are masked out are not counted into the binned value.

    :Authors:
        Max F. Hantke (hantke@xray.bmc.uu.se)
    """
    success, spimage = utils.io.load_spimage()
    if not success:
        print "Skipping analysis.pixel_detector.bin"
        return
    image = evt[type][key].data
    binned_image, binned_mask = spimage.binImage(image, binning, msk=mask, output_binned_mask=True)
    add_record(evt["analysis"], "analysis", "binned image - "+key, binned_image)
    if binned_mask is not None:
        add_record(evt["analysis"], "analysis", "binned mask - "+key, binned_mask)

def radial(evt, type, key, mask=None, cx=None, cy=None):
    """Compute the radial average of a detector image given the center position (and a mask). 
    Adds the records ``evt["analysis"]["radial average - " + key]`` and ``evt["analysis"]["radial distance - " + key]``.

    .. note:: This feature depends on the python package `libspimage <https://github.com/FilipeMaia/libspimage>`_.

    Args:
        :evt:        The event variable
        :type(str):  The event type (e.g. photonPixelDetectors)
        :key(str):   The event key (e.g. CCD)

    Kwargs:
        :mask:    Binary mask, pixels that are masked out are not counted into the radial average.
        :cx(float):  X-coordinate of the center position. If None the center will be in the middle.
        :cy(float):  Y-coordinate of the center position. If None the center will be in the middle.

    :Authors:
        Max F. Hantke (hantke@xray.bmc.uu.se)
    """
    success, spimage = utils.io.load_spimage()
    if not success:
        print "Skipping analysis.pixel_detector.radial"
        return
    image = evt[type][key].data
    r, img_r = spimage.radialMeanImage(image, msk=mask, cx=cx, cy=cy, output_r=True)
    valid = np.isfinite(img_r)
    if valid.sum() > 0:
        r = r[valid]
        img_r = img_r[valid]
    add_record(evt["analysis"], "analysis", "radial distance - " + key, r)
    add_record(evt["analysis"], "analysis", "radial average - "  + key, img_r)

def commonModeCSPAD2x2(evt, type, key, mask=None):
    """Subtraction of common mode using median value of masked pixels (left and right half of detector are treated separately). 
    Adds a record ``evt["analysis"]["cm_corrected - " + key]``.
    
    Args:
      :evt:        The event variable
      :type(str):  The event type (e.g. photonPixelDetectors)
      :key(str):   The event key (e.g. CCD)

    Kwargs:
      :mask: Binary mask
    
    :Authors:
        Max F. Hantke (hantke@xray.bmc.uu.se)
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    data = evt[type][key].data
    dataCorrected = numpy.copy(data)
    lData = data[:,:data.shape[1]/2]
    rData = data[:,data.shape[1]/2:]
    if mask is None:
        lMask = numpy.ones(shape=lData.shape, dtype="bool")
        rMask = numpy.ones(shape=rData.shape, dtype="bool")
    else:
        lMask = mask[:,:data.shape[1]/2] == False
        rMask = mask[:,data.shape[1]/2:] == False
    if lMask.sum() > 0:
        dataCorrected[:,:data.shape[1]/2] -= numpy.median(lData[lMask])
    if rMask.sum() > 0:
        dataCorrected[:,data.shape[1]/2:] -= numpy.median(rData[rMask])    
    add_record(evt["analysis"], "analysis", "cm_corrected - " + key, dataCorrected)

def commonModePNCCD(evt, type, key, outkey=None):
    """Common mode correction for PNCCDs.

    For each row its median value is subtracted (left and right half of detector are treated separately).
    Adds a record ``evt["analysis"][outkey]``.
    
    Args:
      :evt:         The event variable
      :type(str):   The event type (e.g. photonPixelDetectors)
      :key(str):    The event key (e.g. CCD)
      :outkey(str): The event key for the corrected image, default is "corrected - " + key
    
    :Authors:
        Max F. Hantke (hantke@xray.bmc.uu.se)
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    if outkey is None:
        outkey = "corrected - " + key
    data = evt[type][key].data
    dataCorrected = numpy.copy(data)
    lData = data[:,:data.shape[1]/2]
    rData = data[:,data.shape[1]/2:]
    dataCorrected[:,:data.shape[1]/2] -= numpy.median(lData,axis=1).repeat(lData.shape[1]).reshape(lData.shape)
    dataCorrected[:,data.shape[1]/2:] -= numpy.median(rData,axis=1).repeat(rData.shape[1]).reshape(rData.shape)
    add_record(evt["analysis"], "analysis", outkey, dataCorrected)

def backgroundSubtract(evt, record, background=None):
    """Subtraction of background. Adds a record ``evt["analysis"]["bg_subtracted - " + record.name]``.

    Args:
      :evt:        The event variable
      :type(str):  The event type (e.g. photonPixelDetectors)
      :key(str):   The event key (e.g. CCD)

    :Authors:
        Max F. Hantke (hantke@xray.bmc.uu.se)
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    data = evt[type][key].data
    if background is not None:
        dataCorrected = data - background
    else:
        dataCorrected = data
    add_record(evt["analysis"], "analysis", "bg_corrected - " + key, dataCorrected)

def cropAndCenter(evt, data_rec, cx=None, cy=None, w=None, h=None):
    
    data = data_rec.data
    name = data_rec.name
    Ny, Nx = data.shape
    if cx is None:
        cx = (Nx-1)/2.
    if cy is None:
        cy = (Ny-1)/2.
    # Round to .0 / .5    
    cx = np.round(cx * 2)/2.
    cy = np.round(cy * 2)/2.
    if w is None:
        w = Nx
    if h is None:
        h = Ny
    data_cropped = data[cy-h/2:cy+h/2, cx-w/2:cx+w/2]
    add_record(evt["analysis"], "analysis", "cropped/centered", data_cropped)

