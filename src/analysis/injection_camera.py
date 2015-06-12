import numpy as np
import cv2
import scipy.ndimage.measurements
from backend import ureg
from backend import add_record

def getMaskedParticles(evt, type, key, output):
    """Black-box method to create a masked version of a camera
    image where individual illuminated particles constitute a mask."""
    outimg = cv2.adaptiveThreshold(evt[type][key].data.astype(np.uint8), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    add_record(evt["analysis"], "analysis", output, outimg)

# findContours
# eliminate wrong areas

def countContours(evt, type, key, contourKey, outimage, outvector):
    imageoutput = np.ndarray(evt[type][key].data().shape(), np.int16)
    contours = evt["analysis"][contourKey].data()
    for i in xrange(contours.size):
        cv2.drawContours(imageoutput, contours, i, i + 1, cv2.FILLED)
    needed_labels = numpy.arange(1, contours.size + 1)
    counts = scipy.ndimage.measurements.sum(evt[type][key].data(), imageoutput, needed_labels)
    add_record(evt["analysis"], "analysis", outimage, imageoutput)
    add_record(evt["analysis"], "analysis", outvector, counts)
    

# send resulting vector
