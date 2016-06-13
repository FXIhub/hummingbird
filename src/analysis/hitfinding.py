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

def countHits(evt, hit, outkey="nrHits"):
    """Counts hits and adds the total nr. of hits to ``evt["analysis"][outkey]``.

    Args:
        :evt:     The event variable
        :hit:     A boolean (True for hit, False for miss)
    
    Kwargs:
        :outkey(str):  Data key of resulting ``Record``, default is "nrHits" 

    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
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

def hitrate(evt, hit, history=100, unit='percent', outkey="hitrate"):
    """Counts hits and adds current hit rate to ``evt["analysis"][outkey]``.

    Args:
        :evt:     The event variable
        :hit:     A boolean (True for hit, False for miss)
    
    Kwargs:
        :history(int):  Buffer length, default = 100
        :outkey(str):   Data key of resulting ``Record``, default is "hitrate" 
        :unit(str):     Unit of hitrate, 'fraction' or 'percent', default is 'fraction'

    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
        Tomas Ekeberg
    """
    global hitrate_counters
    if outkey not in hitrate_counters or hitrate_counters[outkey].maxlen != history:
        hitrate_counters[outkey] = collections.deque([], history)
    hitrate_counters[outkey].append(bool(hit))
    hitcount = np.array(hitrate_counters[outkey].count(True))
    ipc.mpi.sum("hitcount - " + outkey, hitcount)
    v = evt["analysis"]
    if (ipc.mpi.is_main_worker()):
        hitrate = hitcount[()] / (ipc.mpi.nr_workers() * float(len(hitrate_counters[outkey])))
        if unit == 'fraction':
            add_record(v, "analysis", outkey, hitrate)
        elif unit == 'percent':
            add_record(v, "analysis", outkey, 100.*hitrate)

def countLitPixels(evt, record, aduThreshold=20, hitscoreThreshold=200, hitscoreDark=0, hitscoreMax=None, mask=None, outkey="litpixel: "):
    """A simple hitfinder that counts the number of lit pixels and
    adds the result to ``evt["analysis"][outkey + "isHit"]``,  ``evt["analysis"][outkey + "isMiss"]``, 
    and  the hitscore to ``evt["analysis"][outkey + "hitscore"]``.

    Args:
        :evt:       The event variable
        :record:    A pixel detector ``Record``

    Kwargs:
        :aduThreshold(int):      only pixels above this threshold (in ADUs) are valid, default=20
        :hitscoreThreshold(int): events with hitscore (Nr. of lit pixels)  above this threshold are hits, default=200
        :mask(int, bool):        only use masked pixel (mask == True or 1) for countin
        :outkey(str):            Prefix of data key of resulting ``Record``, default is "litpixel: " 
    
    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    hitscore = (record.data[mask] > aduThreshold).sum()
    hit = int(hitscore > hitscoreThreshold)
    if hitscoreMax is not None:
        hit *= int(hitscore <= hitscoreMax)
    v = evt["analysis"]
    add_record(v, "analysis", outkey + "isHit", hit)
    add_record(v, "analysis", outkey + "isMiss", int(not hit and (hitscore > hitscoreDark)))
    add_record(v, "analysis", outkey + "hitscore", hitscore)

def countTof(evt, record, signalThreshold=1, minWindow=0, maxWindow=-1, hitscoreThreshold=2, outkey="tof: "):
    """A simple hitfinder that performs a peak counting test on a time-of-flight detector signal, in a specific subwindow and adds the result to ``evt["analysis"][outkey + "isHit"]``, and  the hitscore to ``evt["analysis"][outkey + "hitscore"]``.

    Args:
        :evt:       The event variable
        :record:    A ToF detector record

    Kwargs:
        :signalThreshold(str):   The threshold of the signal, anything above this contributes to the score, default=1
        :minWindow(int):         Lower limit of window, default=0
        :maxWindow(int):         Upper limit of window, default=1
        :hitscoreThreshold(int): events with hitscore (Nr. of photons)  above this threshold are hits, default=2
        :outkey(str):            Prefix of data key of resulting ``Record``, default is "tof: " 

    :Authors:
        Carl Nettelblad (carl.nettelblad@it.uu.se)
    """
    hitscore = record.data[minWindow:maxWindow] > signalThreshold
    hit = hitscore > hitscoreThreshold
    v = evt["analysis"]
    add_record(v, "analysis", outkey + "isHit", hit) 
    add_record(v, "analysis", outley + "hitscore", hitscore)
    
def countHitscore(evt, hitscore, hitscoreThreshold=200, outkey=""):
    """A simple hitfinder that performs a limit test against an already defined hitscore 
    and adds the result to ``evt["analysis"][outkey + "isHit"]``, and
    the hitscore to ``evt["analysis"][outkey + "hitscore"]``.

    Args:
        :evt:       The event variable
        :hitscore:  A pre-defined hitscore

    Kwargs:
        :hitscoreThreshold(int):   Events with hitscore above this threshold are hits, default=200
    
    :Authors:
        Carl Nettelblad (carl.nettelblad@it.uu.se)
        Benedikt J. Daurer
    """
    hit = hitscore > hitscoreThreshold
    v = evt["analysis"]
    add_record(v, "analysis", outkey + "isHit", hit) 
    add_record(v, "analysis", outley + "hitscore", hitscore)

def countPhotonsAgainstEnergyFunction(evt, photonscore_record, energy_record, energyFunction = lambda x : 200, outkey='photons: '):
    """A hitfinder that tests given photon score (e.g. photon count) against a predicted photon threshold
    that is dependent on some given energy and
    adds a boolean to ``evt["analysis"][outkey + "isHit"]``,  the hitscore to ``evt["analysis"][outkey + "hitscore"]`` and
    the limit to ``evt["analysis"][outkey + "photonLimit"]

    Args:
        :evt:       The event variable
        :photonscore_record: A ``Record`` containting a photon score, e.g. total photon count
        :energy_record:"     A ``Record`` containting an energy value, e.g. from gas monitor detector 

    Kwargs:
        :energyFunction(function with double argument): function that computes the photon threshold, given the energy
        :outkey(str):            Prefix of data key of resulting ``Record``, default is "photons: " 
    
    :Authors:
        Carl Nettelblad (carl.nettelblad@it.uu.se)
    """
    score  = photonscore_record.data
    energy = energy_record.data
    photonLimit = energyFunction(energy)
    v = evt["analysis"]
    hit = score > photonLimit
    add_record(v, "analysis", outkey + "isHit", hit)
    add_record(v, "analysis", outkey + "photonLimit", photonLimit)
    add_record(v, "analysis", outkey + "hitscore", score)

def countPhotonsAgainstEnergyPolynomial(evt, photonscore_record, energy_record, energyPolynomial = [200], outkey='photons: '):
    """A hitfinder that tests photon score (e.g. photon count) against a predicted photon threshold
    that is dependent on some given energy and 
    adds a boolean to ``evt["analysis"][outkey + "isHit"]``,  the hitscore to ``evt["analysis"][outkey + "hitscore"]`` and
    the limit to ``evt["analysis"][outkey + "photonLimit"]

    Args:
        :evt:       The event variable
        :photonscore_record: A ``Record`` containting a photon score, e.g. total photon count
        :energy_record:"     A ``Record`` containting an energy value, e.g. from gas monitor detector 

    Kwargs:
        :energyPolynomial: array_like with polynomial coefficients fed to polyval (polynomial order one less than list length)
        :outkey(str):            Prefix of data key of resulting ``Record``, default is "photons: " 
    
    :Authors:
        Carl Nettelblad (carl.nettelblad@it.uu.se)
    """
    countPhotonsAgainstEnergyFunction(evt, photonscore_record, energy_record, lambda x : numpy.polyval(energyPolynomial, x), outkey=outkey)

import numpy

def generate_radial_mask(mask,cx,cy,radius):
    [dimy,dimx] = mask.shape

    x = numpy.arange(dimx)-cx
    y = numpy.arange(dimy)-cy
    X,Y = numpy.meshgrid(x,y)
    R = numpy.sqrt(X**2+Y**2)

    mask2 = mask.copy()
    mask2[R > radius] = 0
    return mask2
