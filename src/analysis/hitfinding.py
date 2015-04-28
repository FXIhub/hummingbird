import ipc
import numpy
#from backend import Worker
from scipy.sparse import lil_matrix
#from plots import MeanMap

counter = []
def counting(hit):
    if hit: counter.append(True)
    else: counter.append(False)
    return counter

# JAS: made countLitPixels independent of Worker module by using arguments instead of state keys/values
def countLitPixels(image, thresholdADU=20, thresholdLitPixels=200):
    hitscore = (image > thresholdADU).sum()
    return hitscore > thresholdLitPixels, hitscore

correlation = []
xArray = []
yArray = []
def correlate(x, y):
    xArray.append(x)
    yArray.append(y)
    correlation.append(x*y/(numpy.mean(xArray)*numpy.mean(yArray)))
    return correlation

initialized = False
correlation2D = None
def correlate2D(x, y, xMin=0, xMax=1, xNbins=10, yMin=0, yMax=1, yNbins=10):
    global correlation2D, initialized
    if not initialized:
        # initiate (y, x) in 2D array to get correct orientation of image
        correlation2D = numpy.zeros((yNbins, xNbins), dtype=int)
        initialized = True
    deltaX = (xMax - float(xMin))/xNbins
    deltaY = (yMax - float(yMin))/yNbins
    nx = numpy.ceil((x - xMin)/deltaX)
    if (nx < 0):
        nx = 0
    elif (nx >= xNbins):
        nx = xNbins - 1
    ny = numpy.ceil((y - yMin)/deltaY)
    if (ny < 0):
        ny = 0
    elif (ny >= yNbins):
        ny = yNbins - 1
    # assign y to row and x to col in 2D array
    correlation2D[ny, nx] += 1
    return correlation2D

def plotHitscore(hitscore):
    ipc.new_data("Hitscore", hitscore)

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
