import ipc
import numpy
from backend import Backend
from scipy.sparse import lil_matrix
#from plots import MeanMap

counter = []
def counting(hit):
    if hit: counter.append(True)
    else: counter.append(False)
    return counter

def countLitPixels(image):
    hitscore = (image > Backend.state["aduThreshold"]).sum()
    return hitscore > Backend.state["hitscoreMinCount"], hitscore

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
