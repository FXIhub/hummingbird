# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import numpy as np
from numpy import max, mean, min, std, sum

from hummingbird import utils
from hummingbird.backend import add_record, ureg


def printStatistics(detectors):
    for k,r in detectors.items():
        v = r.data
        print("%s (%s): sum=%g mean=%g min=%g max=%g std=%g" % (k, r.unit,
                                                                sum(v), mean(v),
                                                                min(v), max(v),
                                                                std(v)))


def pnccdGain(evt, record, gainmode):
    """Returns gain (Number of ADUs per photon) based on photon energy record and gain mode.
    
    Args:
        :evt:    The event variable
        :record: A photon energy ``Record`` given in eV
        :gainmode: The gain mode of PNCCD (3,4,5,6) or 0 for no gain
    """
    maximum_gain = 1250  # at photon energy of 1keV
    if gainmode == 6:   # 1/1
        gain = maximum_gain
    elif gainmode == 5 :# 1/4
        gain = maximum_gain/4
    elif gainmode == 4: # 1/16
        gain = maximum_gain/16
    elif gainmode == 3: # 1/64
        gain = maximum_gain/64
    elif gainmode == 2: # 1/128
        gain = maximum_gain/128
    elif gainmode == 1: # 1/256
        gain = maximum_gain/256
    elif gainmode == 0:
        gain = 1.
    gain = gain * (record.data / 1000.) # Rescale gain given a photon energy in eV
    add_record(evt['analysis'], 'analysis', 'gain', gain)

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

    
def totalNrPhotons(evt, record, aduPhoton=1, aduThreshold=0.5, outkey=None):
    """Estimates the total nr. of photons on the detector and adds it to ``evt["analysis"][outkey]``.

    Args:
        :evt:       The event variable
        :record:    The data record (e.g. evt['photonPixelDetectors']['CCD'])

    Kwargs:
        :aduPhoton(int):    ADU count per photon, default = 1
        :aduThreshold(int): only pixels above this threshold given in units of ADUs are valid, default = 0.5
        :outkey(str):       Data key of resulting data record, default is 'nrPhotons' 
    
    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    if outkey is None:
        outkey = 'nrPhotons'
    data  = record.data.flat
    valid = data > aduThreshold
    add_record(evt["analysis"], "analysis", outkey, sum(data[valid]) / float(aduPhoton))

def maxPhotonValue(evt, record, aduPhoton=1, outkey=None):
    """Estimates the maximum number of photons on one pixel on the detector and adds it to ``evt["analysis"][outkey]``.

    Args:
        :evt:       The event variable
        :record:    The data record (e.g. evt['photonPixelDetectors']['CCD'])

    Kwargs:
        :aduPhoton(int):  ADU count per photon, default = 1
        :outkey(str):     Data key of resulting data record, default is 'maxPhotons' 
    
    :Authors:
        Tomas Ekeberg (ekeberg@xray.bmc.uu.se)
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    if outkey is None:
        outkey = 'maxPhotons'
    data = record.data.flat
    add_record(evt["analysis"], "analysis", outkey, max(data) / float(aduPhoton))

def threshold(evt, record, threshold, outkey=None):
    """Set all values in an array that are lower than the threshold to zero.
    
    Args:
        :evt:       The event variable
        :record:    The data record
        :threshold: Set everything lower than this number to zero

    Kwargs:
        :aduPhoton(int):  ADU count per photon, default = 1
        :outkey(str):     Data key of resulting data record, default is 'maxPhotons' 
    
    :Authors:
        Tomas Ekeberg (ekeberg@xray.bmc.uu.se)
    """
    if outkey is None:
        outkey = "thresholded"
    data_clean = record.data.copy()
    data_clean[data_clean < threshold] = 0.
    rec = add_record(evt["analysis"], "analysis", outkey, data_clean)
    return rec

initialized = {}
def assemble(evt, type, key, x, y, nx=None, ny=None, subset=None, outkey=None, initkey=None):
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
    if initkey is None: 
        initkey = key
    
    if not initkey in initialized:
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
        initialized[initkey] = {
            'assembled':assembled,
            'height':height,
            'width':width,
            'shape':shape,
            'y':y_ss,
            'x':x_ss
        }
    assembled = initialized[initkey]['assembled']
    height = initialized[initkey]['height']
    width = initialized[initkey]['width']
    shape = initialized[initkey]['shape']
    y = initialized[initkey]['y']
    x = initialized[initkey]['x']

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
        print("Skipping analysis.pixel_detector.bin")
        return
    image = evt[type][key].data
    binned_image, binned_mask = spimage.binImage(image, binning, msk=mask, output_binned_mask=True)
    add_record(evt["analysis"], "analysis", "binned image - "+key, binned_image)
    if binned_mask is not None:
        add_record(evt["analysis"], "analysis", "binned mask - "+key, binned_mask)

def radial(evt, record, mask=None, cx=None, cy=None, key=''):
    """Compute the radial average of a detector image given the center position (and a mask). 
    Adds the records ``evt["analysis"]["radial average - " + key]`` and ``evt["analysis"]["radial distance - " + key]``.

    .. note:: This feature depends on the python package `libspimage <https://github.com/FilipeMaia/libspimage>`_.

    TODO: Updated docstring

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
        print("Skipping analysis.pixel_detector.radial")
        return
    image = record.data
    r, img_r = spimage.radialMeanImage(image, msk=mask, cx=cx, cy=cy, output_r=True)
    valid = np.isfinite(img_r)
    if valid.sum() > 0:
        r = r[valid]
        img_r = img_r[valid]
    r_rec = add_record(evt["analysis"], "analysis", "radial distance - " + key, r)
    img_rec = add_record(evt["analysis"], "analysis", "radial average - "  + key, img_r)
    return r_rec, img_rec




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
    dataCorrected = np.copy(data)
    lData = data[:,:data.shape[1]/2]
    rData = data[:,data.shape[1]/2:]
    if mask is None:
        lMask = np.ones(shape=lData.shape, dtype="bool")
        rMask = np.ones(shape=rData.shape, dtype="bool")
    else:
        lMask = mask[:,:data.shape[1]/2] == False
        rMask = mask[:,data.shape[1]/2:] == False
    if lMask.sum() > 0:
        dataCorrected[:,:data.shape[1]/2] -= np.median(lData[lMask])
    if rMask.sum() > 0:
        dataCorrected[:,data.shape[1]/2:] -= np.median(rData[rMask])    
    add_record(evt["analysis"], "analysis", "cm_corrected - " + key, dataCorrected)


def commonModeLines(evt, record, outkey=None, direction='vertical'):
    """Common mode correction subtracting the median along lines.

    Args:
       :evt:      The event variable
       :record:   A pixel detector ``Record```
       
    Kwargs:
      :outkey:    The event key for the corrected detecor image, default is "corrected"
      :direction: The direction of the lines across which median is taken, default is vertical  
    """
    if outkey is None:
        outkey = "corrected"
    data = record.data
    dataCorrected = np.copy(data)
    if direction is 'vertical':
        dataCorrected -= np.transpose(np.median(data,axis=0).repeat(data.shape[0]).reshape(data.shape))
    elif direction is 'horizontal':
        dataCorrected -= np.median(data,axis=1).repeat(data.shape[1]).reshape(data.shape)
    add_record(evt["analysis"], "analysis", outkey, dataCorrected)


def _cmc(img, msk=None, axis=1, signal_threshold=None, min_nr_pixels_per_median=1):

    # Valid input?
    if axis not in [0,1]:
        logging.error("axis=%s is invalid input." % str(axis))
        return

    # Transpose if necessary
    if axis == 0:
        imgt = img.transpose()
        if msk is not None:
            mskt = msk.transpose()
        else:
            mskt = None
        tmpimg = np.copy(imgt)
        tmpmsk = mskt
    else:
        tmpimg = np.copy(img)
        tmpmsk = msk

    excl_calc = np.zeros(dtype='bool', shape=tmpimg.shape)
    excl_corr = np.zeros(dtype='bool', shape=tmpimg.shape)
    # Exclude pixels from median calculation
    if signal_threshold is not None:
        # Pixels that shall be excluded for median calculation
        excl_calc = (tmpimg-np.median(tmpimg) > signal_threshold)
    if msk is not None:
        excl_calc |= (tmpmsk==False)
    if min_nr_pixels_per_median >= 1:
        # Pixels that shall not be cmc corrected
        excl_corr = ((tmpimg.shape[1]-excl_calc.sum(axis=1)) <= min_nr_pixels_per_median).repeat(tmpimg.shape[1]).reshape(tmpimg.shape)
        # For avoiding warning when calculating median with no values
        if excl_corr.any():
            excl_calc[excl_corr] = False
    np.putmask(tmpimg, excl_calc, np.nan)

    # Calculate medians
    cm = np.nanmedian(tmpimg, axis=1).repeat(tmpimg.shape[1]).reshape(tmpimg.shape)

    # Exclude pixels from correction
    if msk is not None:
        excl_corr |= (tmpmsk==False)
    excl_corr |= np.isnan(cm)
    np.putmask(cm, excl_corr, 0.)
    
    # Subtract common mode
    if axis == 0:
        imgt -= cm
    else:
        img -= cm
    
def commonModePNCCD(evt, type, key, outkey=None, transpose=False, signal_threshold=None, mask=None, min_nr_pixels_per_median=1):
    """Common mode correction for PNCCDs.

    For each row its median value is subtracted (left and right half of detector are treated separately).
    Adds a record ``evt["analysis"][outkey]``.
    
    Args:
      :evt:                     The event variable
      :type(str):               The event type (e.g. photonPixelDetectors)
      :key(str):                The event key (e.g. CCD)

    Kwargs:
      :outkey(str):             The event key for the corrected image, default is "corrected - " + key
      :transpose(bool):         Apply procedure on transposed image
      :signal_threshold(float): Apply procedure by using only pixels below given value
      :mask:                    You may provide a boolean mask with values that shall be excluded from common mode correction
      :min_nr_pixels_per_median(int): Common mode correction will be skipped for pixel lines that do not contain as much as this number of values
    
    :Authors:
        Max F. Hantke (hantke@xray.bmc.uu.se)
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    if outkey is None:
        outkey = "corrected - " + key
    data = evt[type][key].data

    dataCorrected = np.copy(data)
    lData = dataCorrected[:,:data.shape[1]/2]
    rData = dataCorrected[:,data.shape[1]/2:]
    if mask is not None:
        lMask = mask[:,:data.shape[1]/2]
        rMask = mask[:,data.shape[1]/2:]
    else:
        lMask = None
        rMask = None
    _cmc(lData, msk=lMask, axis=1 if not transpose else 0, signal_threshold=signal_threshold, min_nr_pixels_per_median=min_nr_pixels_per_median)
    _cmc(rData, msk=rMask, axis=1 if not transpose else 0, signal_threshold=signal_threshold, min_nr_pixels_per_median=min_nr_pixels_per_median)
    
    add_record(evt["analysis"], "analysis", outkey, dataCorrected)

def commonModePNCCD2(evt, type, key, outkey=None, signal_threshold=None, mask=None, min_nr_pixels_per_median=1):
    """Common mode correction for PNCCDs.

    For each row its median value is subtracted (left and right half of detector are treated separately).
    Adds a record ``evt["analysis"][outkey]``.
    
    Args:
      :evt:                     The event variable
      :type(str):               The event type (e.g. photonPixelDetectors)
      :key(str):                The event key (e.g. CCD)

    Kwargs:
      :outkey(str):             The event key for the corrected image, default is "corrected - " + key
      :transpose(bool):         Apply procedure on transposed image
      :signal_threshold(float): Apply procedure by using only pixels below given value
      :mask:                    You may provide a boolean mask with values that shall be excluded from common mode correction
      :min_nr_pixels_per_median(int): Common mode correction will be skipped for pixel lines that do not contain as much as this number of values
    
    :Authors:
        Max F. Hantke (hantke@xray.bmc.uu.se)
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    if outkey is None:
        outkey = "corrected - " + key
    data = evt[type][key].data

    dataCorrected = np.copy(data)
    quads = [dataCorrected[:data.shape[0]/2,:data.shape[1]/2],
             dataCorrected[data.shape[0]/2:,:data.shape[1]/2],
             dataCorrected[:data.shape[0]/2,data.shape[1]/2:],
             dataCorrected[data.shape[0]/2:,data.shape[1]/2:]]
    if mask is not None:
        mquads = [mask[:data.shape[0]/2,:data.shape[1]/2],
                  mask[data.shape[0]/2:,:data.shape[1]/2],
                  mask[:data.shape[0]/2,data.shape[1]/2:],
                  mask[data.shape[0]/2:,data.shape[1]/2:]]
    else:
        mquads = [None, None, None, None]
    for quad,mquad in zip(quads,mquads):
        _cmc(quad, msk=mquad, axis=0, signal_threshold=signal_threshold, min_nr_pixels_per_median=min_nr_pixels_per_median)
        _cmc(quad, msk=mquad, axis=1, signal_threshold=signal_threshold, min_nr_pixels_per_median=min_nr_pixels_per_median)
    
    add_record(evt["analysis"], "analysis", outkey, dataCorrected)

    
def subtractImage(evt, type, key, image, outkey=None):
    """Subtract an image.

    Adds a record ``evt["analysis"][outkey]``.

    Args:
      :evt:        The event variable
      :type(str):  The event type (e.g. photonPixelDetectors)
      :key(str):   The event key (e.g. CCD)
    
     Kwargs:
      :outkey(str): The event key for the subtracted image, default is "subtraced - " + key

    :Authors:
        Max F. Hantke (hantke@xray.bmc.uu.se)
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    if outkey is None:
        outkey = "subtracted - " + key
    data = evt[type][key].data
    dataCorrected = data - image
    add_record(evt["analysis"], "analysis", outkey, dataCorrected)

def cropAndCenter(evt, data_rec, cx=None, cy=None, w=None, h=None, outkey='cropped'):
    
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
    data_cropped = data[int(round(cy-h/2)):int(round(cy+h/2)), int(round(cx-w/2)):int(round(cx+w/2))]
    add_record(evt["analysis"], "analysis", outkey, data_cropped)

def rotate90(evt, data_rec, k=1, outkey='rotated'):
    data_rotated = np.rot90(data_rec.data,k)
    return add_record(evt["analysis"], "analysis", outkey, data_rotated)
    
def moveHalf(evt, record, vertical=0, horizontal=0, outkey='half-moved', transpose=False):
    data = record.data
    if transpose:
        data = np.transpose(data)
    ny,nx = data.shape
    data_moved = np.zeros((ny + abs(vertical), nx + horizontal), dtype=data.dtype)
    if horizontal < 0: horizontal = 0
    if vertical < 0:
        data_moved[-vertical:,:nx/2] = data[:,:nx/2]
        data_moved[:vertical,nx/2+horizontal:] = data[:,nx/2:]
    elif vertical > 0:
        data_moved[:-vertical,:nx/2] = data[:,:nx/2]
        data_moved[vertical:,nx/2+horizontal:] = data[:,nx/2:]
    else:
        data_moved[:,:nx/2] = data[:,:nx/2]
        data_moved[:,nx/2+horizontal:] = data[:,nx/2:]
    if transpose:
        data_moved = np.transpose(data_moved)
    return add_record(evt["analysis"], "analysis", outkey, data_moved)  
