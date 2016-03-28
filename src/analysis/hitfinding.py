# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
import ipc
import numpy as np
import collections
from backend import add_record

hitrate_counters = {}
hit_counters = {}

def countHits(evt, hit, history=100, outkey="nrHits"):
    """Takes a boolean (True for hit, False for miss) and adds accumulated nr. of hits

    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se),
        Jonas Sellberg 
        Tomas Ekeberg
    """
    global hit_counters
    if outkey not in hit_counters:
        hit_counters[outkey] = 0
    if hit:
        hit_counters[outkey] += 1
    v = evt["analysis"]
    add_record(v, "analysis", outkey, hit_counters[outkey])

def hitrate(evt, hit, history=100, outkey="hitrate"):
    global hitrate_counters
    if outkey not in hitrate_counters or hitrate_counters[outkey].maxlen != history:
        hitrate_counters[outkey] = collections.deque([], history)
    hitrate_counters[outkey].append(bool(hit))
    hitrate = np.array(hitrate_counters[outkey].count(True)/float(len(hitrate_counters[outkey])))
    ipc.mpi.sum("hitrate", hitrate)
    v = evt["analysis"]
    if (ipc.mpi.is_main_worker()):
        add_record(v, "analysis", outkey, hitrate[()]/ipc.mpi.nr_workers())

def countLitPixels(evt, data_rec, aduThreshold=20, hitscoreThreshold=200, hitscoreDark=0, hitscoreMax=None, mask=None, outkey=None):
    """A simple hitfinder that counts the number of lit pixels and
    adds a boolean to ``evt["analysis"][outkey + "isHit"]``,  ``evt["analysis"][outkey + "isMiss"]`` 
    and  the hitscore to ``evt["analysis"][outkey + "hitscore"]``.

    Args:
        :evt:       The event variable
        :type(str): The event type (e.g. photonPixelDetectors)
        :key(str):  The event key (e.g. CCD)
    Kwargs:
        :aduThreshold(int):      only pixels above this threshold (in ADUs) are valid, default=20
        :hitscoreThreshold(int): events with hitscore (Nr. of lit pixels)  above this threshold are hits, default=200
        :mask(int, bool):        only use masked pixel (mask == True or 1) for counting
        :outkey(str):            event key for results, default is "" 
    
    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    if outkey is None:
        outkey = ""
    hitscore = (data_rec.data[mask] > aduThreshold).sum()
    v = evt["analysis"]
    hit = int(hitscore > hitscoreThreshold)
    if hitscoreMax is not None:
        hit *= int(hitscore <= hitscoreMax)

    add_record(v, "analysis", outkey + "isHit", hit)
    add_record(v, "analysis", outkey + "isMiss", int(not hit and (hitscore > hitscoreDark)))
    add_record(v, "analysis", outkey + "hitscore", hitscore)


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
