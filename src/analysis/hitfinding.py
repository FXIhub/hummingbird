import ipc
from backend import Record
import numpy as np


counter = []
def counting(hit):
    if hit: counter.append(True)
    else: counter.append(False)
    return counter

def countLitPixels(detector, aduThreshold=20, litPixelThreshold=200):
    """Finding hits by counting nr. of lit pixels on the detector

    Args:
        :detector(Record):  A detector record
    Kwargs:
        :aduThreshold(int):      only pixels above this threshold are valid, default=20
        :litPixelThreshold(int): events with lit pixels above this threshold are hits, default=200
    Returns:
        bool hit, Record hitscore
    """
    hitscore = (detector.data > aduThreshold).sum()
    return hitscore > litPixelThreshold, Record("hitscore - " + detector.name, hitscore)


correlation = []
xArray = []
yArray = []
def correlate(x, y):
    xArray.append(x)
    yArray.append(y)
    correlation.append(x*y/(np.mean(xArray)*np.mean(yArray)))
    return correlation

initialized = False
correlation2D = None
def correlate2D(x, y, xMin=0, xMax=1, xNbins=10, yMin=0, yMax=1, yNbins=10):
    global correlation2D, initialized
    if not initialized:
        # initiate (y, x) in 2D array to get correct orientation of image
        correlation2D = np.zeros((yNbins, xNbins), dtype=int)
        initialized = True
    deltaX = (xMax - float(xMin))/xNbins
    deltaY = (yMax - float(yMin))/yNbins
    nx = np.ceil((x - xMin)/deltaX)
    if (nx < 0):
        nx = 0
    elif (nx >= xNbins):
        nx = xNbins - 1
    ny = np.ceil((y - yMin)/deltaY)
    if (ny < 0):
        ny = 0
    elif (ny >= yNbins):
        ny = yNbins - 1
    # assign y to row and x to col in 2D array
    correlation2D[ny, nx] += 1
    return correlation2D
