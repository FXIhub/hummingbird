# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import cv2
import numpy as np
import scipy.ndimage.measurements

from hummingbird.backend import add_record, ureg


def getMaskedParticles(evt, type, key, output, thresh = 20, minX = 800, maxX = 1500, minY = 0, maxY = 1700, kw = 5):
    """Black-box method to create a masked version of a camera
    image where individual illuminated particles constitute a mask."""
    outimg = np.zeros(evt[type][key].data.shape, np.dtype(np.uint8))
    kernel = np.ones((kw*2+1,kw*2+1), np.uint8)
    outimg[minY:maxY, minX:maxX] = evt[type][key].data[minY:maxY,minX:maxX] > thresh
    outimg = cv2.dilate(outimg, kernel)
    add_record(evt["analysis"], "analysis", output, outimg)

def countContours(evt, type, key, maskedKey, outimage, outvector):
    imageoutput = np.ndarray(evt[type][key].data.shape, np.uint8)
    (contours,_) = cv2.findContours(evt["analysis"][maskedKey].data, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    for i in xrange(len(contours)):
        cv2.drawContours(imageoutput, contours, i, i + 1, -1)
    needed_labels = np.arange(1, len(contours))
    counts = scipy.ndimage.measurements.sum(evt[type][key].data, imageoutput, needed_labels)
    add_record(evt["analysis"], "analysis", outimage, imageoutput)
    add_record(evt["analysis"], "analysis", outvector, counts)
