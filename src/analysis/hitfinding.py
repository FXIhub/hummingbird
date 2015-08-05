import ipc
from backend import add_record
import numpy as np
import collections

counter = collections.deque([])
counter_good = collections.deque([])
def countHits(evt, hit, good_hit=True, history=100):
    """Takes a boolean (True for hit, False for miss) and adds accumulated nr. of hits to ``evt["analysis"]["nrHit"]`` and 
    accumulated nr. of misses to ``evt["analysis"]["nrMiss"]``

    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se),
        Jonas Sellberg 
    """
    global counter
    global counter_good
    if counter.maxlen is None or (counter.maxlen != history):
        counter = collections.deque([], history)
        counter_good = collections.deque([], history)
    counter.append(bool(hit))
    counter_good.append(bool(good_hit))
    v = evt["analysis"]
    add_record(v, "analysis", "nrHit", counter.count(True))
    add_record(v, "analysis", "nrMiss", counter.count(False))
    add_record(v, "analysis", "nrGoodHit", counter_good.count(True))
    add_record(v, "analysis", "nrGoodMiss", counter_good.count(False))

def hitrate(evt, hit, good_hit=True, history=100):
    """Takes a boolean (True for hit, False for miss) and adds the hit rate in % to ``evt["analysis"]["hitrate"]`` if called by main worker, otherwise it returns None. Has been tested in MPI mode

    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    countHits(evt, hit, good_hit=good_hit, history=history/ipc.mpi.nr_workers())
    hits = evt["analysis"]["nrHit"].data
    misses = evt["analysis"]["nrMiss"].data    
    good_hits = evt["analysis"]["nrGoodHit"].data
    good_misses = evt["analysis"]["nrGoodMiss"].data
    hitrate = np.array(100 * hits / float(hits + misses))
    good_hitrate = np.array(100 * good_hits / float(good_hits + good_misses))
    ipc.mpi.sum(hitrate)
    ipc.mpi.sum(good_hitrate)
    v = evt["analysis"]
    if(ipc.mpi.is_main_worker()):
        add_record(v, "analysis", "hitrate", hitrate[()]/ipc.mpi.nr_workers(), unit='%')
        add_record(v, "analysis", "good hitrate", good_hitrate[()]/ipc.mpi.nr_workers(), unit='%')
    else:
        add_record(v, "analysis", "hitrate", None)
        add_record(v, "analysis", "good hitrate", None)

def countLitPixels(evt, type, key, aduThreshold=20, hitscoreThreshold=200, hitscoreDark=0, hitscoreMax=None, mask=None,
                   label=""):
    """A simple hitfinder that counts the number of lit pixels and
    adds a boolean to ``evt["analysis"]["isHit" + key]`` and  the hitscore to ``evt["analysis"]["hitscore - " + key]``.

    Args:
        :evt:       The event variable
        :type(str): The event type (e.g. photonPixelDetectors)
        :key(str):  The event key (e.g. CCD)
    Kwargs:
        :aduThreshold(int):      only pixels above this threshold (in ADUs) are valid, default=20
        :hitscoreThreshold(int): events with hitscore (Nr. of lit pixels)  above this threshold are hits, default=200
        :mask(int, bool):        only use masked pixel (mask == True or 1) for counting
    
    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    detector = evt[type][key]
    hitscore = (detector.data[mask] > aduThreshold).sum()
    v = evt["analysis"]
    #v["isHit - "+key] = hitscore > hitscoreThreshold
    hit = int(hitscore > hitscoreThreshold)
    if hitscoreMax is not None:
        hit *= int(hitscore <= hitscoreMax)
    add_record(v, "analysis", label+"isHit - "+key, hit)
    add_record(v, "analysis", label+"isMiss - "+key, int(hit and (hitscore > hitscoreDark)))
    add_record(v, "analysis", label+"hitscore - "+key, hitscore)

def countTof(evt, type="ionTOFs", key="tof", signalThreshold = 1, minWindow = 0, maxWindow = -1, hitscoreThreshold=2):
    """A simple hitfinder that performs a peak counting test on a time-of-flight detector signal, in a specific subwindow.
    Adds a boolean to ``evt["analysis"]["isHit" + key]`` and  the hitscore to ``evt["analysis"]["hitscore - " + key]``.

    Args:
        :evt:       The event variable
        :type(str): The event type (e.g. ionTOFs)
        :key(str):  The event key (e.g. tof)


    Kwargs:
        :signalThreshold(str): The threshold of the signal, anything above this contributes to the score
        :hitscoreThreshold(int): events with hitscore (Nr. of photons)  above this threshold are hits, default=200
    
    :Authors:
        Carl Nettelblad (carl.nettelblad@it.uu.se)
    """
    v = evt[type][key]
    hitscore = v.data[minWindow:maxWindow] > signalThreshold
    v = evt["analysis"]
    v["isHit - "+key] = hitscore > hitscoreThreshold
    add_record(v, "analysis", "hitscore - "+key, hitscore)

def countPhotons(evt, type, key, hitscoreThreshold=200):
    """A simple hitfinder that performs a limit test against an already defined
    photon count for detector key. Adds a boolean to ``evt["analysis"]["isHit" + key]`` and
    the hitscore to ``evt["analysis"]["hitscore - " + key]``.

    Args:
        :evt:       The event variable
        :type(str): The event type (e.g. photonPixelDetectors)
        :key(str):  The event key (e.g. CCD)
    Kwargs:
        :hitscoreThreshold(int): events with hitscore (Nr. of photons)  above this threshold are hits, default=200
    
    :Authors:
        Carl Nettelblad (carl.nettelblad@it.uu.se)
    """
    v = evt["analysis"]
    hitscore = v["nrPhotons - "+key]    
    v["isHit - "+key] = hitscore > hitscoreThreshold
    add_record(v, "analysis", "hitscore - "+key, hitscore)

def countPhotonsAgainstEnergyFunction(evt, type, key, energyKey = "averagePulseEnergy", energyFunction = lambda x : 200):
    """A hitfinder that tests photon count against a predicted photon threshold
    that is dependent on some existing key
    adds a boolean to ``evt["analysis"]["isHit" + key]``,  the hitscore to ``evt["analysis"]["hitscore - " + key]`` and
    the limit to ``evt["analysis"]["photonLimit - " + key]

    Args:
        :evt:       The event variable
        :type(str): The event type (e.g. photonPixelDetectors)
        :key(str):  The event key (e.g. CCD)
    Kwargs:
	:energyKey(str): The analysis key where the pulse energy is expected to be found
        :energyFunction(function with double argument): function that computes the photon threshold, given the energy
    
    :Authors:
        Carl Nettelblad (carl.nettelblad@it.uu.se)
    """
    v = evt["analysis"]
    hitscore = v["nrPhotons - "+key]
    photonLimit = energyFunction(v[energyKey])
    v["isHit - "+key] = hitscore > photonLimit
    add_record(v, "analysis", "photonLimit - "+key, photonLimit)
    add_record(v, "analysis", "hitscore - "+key, hitscore)

def countPhotonsAgainstEnergyPolynomial(evt, type, key, energyKey = "averagePulseEnergy", energyPolynomial = [200]):
    """A hitfinder that tests photon count against a predicted photon threshold
    that is dependent on some existing key
    adds a boolean to ``evt["analysis"]["isHit" + key]``,  the hitscore to ``evt["analysis"]["hitscore - " + key]`` and
    the limit to ``evt["analysis"]["photonLimit - " + key]

    Args:
        :evt:       The event variable
        :type(str): The event type (e.g. photonPixelDetectors)
        :key(str):  The event key (e.g. CCD)
    Kwargs:
        :energyPolynomial: array_like with polynomial coefficients fed to polyval (polynomial order one less than list length)
    
    :Authors:
        Carl Nettelblad (carl.nettelblad@it.uu.se)
    """
    countPhotonsAgainstEnergyFunction(evt, type, key, energyKey, lambda x : numpy.polyval(energyPolynomial, x))
