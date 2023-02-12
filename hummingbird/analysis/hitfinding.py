# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import collections

import numpy as np

from hummingbird import ipc
from hummingbird.backend import add_record

hitrate_counters = {}
hit_counters = {}

def countHits(evt, hit, outkey="nrHits"):
    """Counts hits and adds the total nr. of hits to ``evt["analysis"][outkey]``.

    Args:
        :evt:     The event variable
        :hit:     A boolean (True for hit, False for miss)
    
    Kwargs:
        :outkey(str):  Data key of resulting :func:`~backend.Record` object, default is "nrHits" 

    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se),
        Jonas Sellberg,
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
        :outkey(str):   Data key of resulting :func:`~backend.Record` object, default is "hitrate" 
        :unit(str):     Unit of hitrate, 'fraction' or 'percent', default is 'percent'

    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se),
        Tomas Ekeberg
    """
    hit = np.atleast_1d(hit)
    global hitrate_counters
    if outkey not in hitrate_counters or hitrate_counters[outkey].maxlen != history:
        hitrate_counters[outkey] = collections.deque([], history)
    for h in hit:
        hitrate_counters[outkey].append(bool(h))
    hitcount = np.array(hitrate_counters[outkey].count(True))
    ipc.mpi.sum("hitcount - " + outkey, hitcount)
    v = evt["analysis"]
    if (ipc.mpi.is_main_event_reader()):
        hitrate = hitcount[()] / (ipc.mpi.nr_event_readers() * float(len(hitrate_counters[outkey])))
        if unit == 'fraction':
            add_record(v, "analysis", outkey, hitrate)
        elif unit == 'percent':
            add_record(v, "analysis", outkey, 100.*hitrate)

def countLitPixels(evt, record, aduThreshold=20, hitscoreThreshold=200, hitscoreDark=0, hitscoreMax=None, mask=None, stack=False, outkey="litpixel: "):
    """A simple hitfinder that counts the number of lit pixels and
    adds the result to ``evt["analysis"][outkey + "isHit"]``,  ``evt["analysis"][outkey + "isMiss"]``, 
    and  the hitscore to ``evt["analysis"][outkey + "hitscore"]``.

    Args:
        :evt:       The event variable
        :record:    A pixel detector :func:`~backend.Record` object

    Kwargs:
        :aduThreshold(int):      only pixels above this threshold (in ADUs) are valid, default=20
        :hitscoreThreshold(int): events with hitscore (Nr. of lit pixels) above this threshold are hits, default=200
        :hitscoreMax(int):       events with hitscore (Nr. of lit pixels) below this threshold (if not None) are hits, default=None
        :hitscoreDark(int):      events with hitscore (Nr. of lit pixels) above this threshold are not darks (so either hit or miss), default=0
        :mask(int, bool):        only use masked pixel (mask == True or 1) for counting the nr. of lit pixels
        :outkey(str):            Prefix of data key of resulting :func:`~backend.Record` object, default is "litpixel: " 
    
    :Authors:
        Benedikt J. Daurer (benedikt@xray.bmc.uu.se)
    """
    
    if(mask is None):
        mask = 1
    hitscore = ((record.data*mask) > aduThreshold).sum(axis=(0,1) if stack is True else None)

    hit = np.array(hitscore > hitscoreThreshold, dtype='int')
    if hitscoreMax is not None:
        hit *= np.array(hitscore <= hitscoreMax, dtype='int')
    miss = np.array((~hit) & (hitscore > hitscoreDark), dtype='int')
    v = evt["analysis"]
    add_record(v, "analysis", outkey + "isHit", hit)
    add_record(v, "analysis", outkey + "isMiss", miss)
    add_record(v, "analysis", outkey + "hitscore", hitscore)

def countTof(evt, record, signalThreshold=1, minWindow=0, maxWindow=-1, hitscoreThreshold=2, outkey="tof: "):
    """A simple hitfinder that performs a peak counting test on a time-of-flight detector signal, 
    in a specific subwindow and adds the result to ``evt["analysis"][outkey + "isHit"]``, 
    and  the hitscore to ``evt["analysis"][outkey + "hitscore"]``.

    Args:
        :evt:       The event variable
        :record:    A ToF detector :func:`~backend.Record` object

    Kwargs:
        :signalThreshold(str):   The threshold of the signal, anything above this contributes to the score, default=1
        :minWindow(int):         Lower limit of window, default=0
        :maxWindow(int):         Upper limit of window, default=1
        :hitscoreThreshold(int): events with hitscore (Nr. of photons)  above this threshold are hits, default=2
        :outkey(str):            Prefix of data key of resulting :func:`~backend.Record` object, default is "tof: " 

    :Authors:
        Carl Nettelblad (carl.nettelblad@it.uu.se)
    """
    hitscore = record.data[minWindow:maxWindow] > signalThreshold
    hit = hitscore > hitscoreThreshold
    v = evt["analysis"]
    add_record(v, "analysis", outkey + "isHit", hit) 
    add_record(v, "analysis", outkey + "hitscore", hitscore)
    
def countHitscore(evt, hitscore, hitscoreThreshold=200, outkey="predef: "):
    """A simple hitfinder that performs a limit test against an already defined hitscore 
    and adds the result to ``evt["analysis"][outkey + "isHit"]``, and
    the hitscore to ``evt["analysis"][outkey + "hitscore"]``.

    Args:
        :evt:       The event variable
        :hitscore:  A pre-defined hitscore

    Kwargs:
        :hitscoreThreshold(int):   Events with hitscore above this threshold are hits, default=200
        :outkey(str):              Prefix of data key of resulting :func:`~backend.Record` object, default is "predef: " 
    
    :Authors:
        Carl Nettelblad (carl.nettelblad@it.uu.se),
        Benedikt J. Daurer
    """
    hit = hitscore > hitscoreThreshold
    v = evt["analysis"]
    add_record(v, "analysis", outkey + "isHit", hit) 
    add_record(v, "analysis", outkey + "hitscore", hitscore)

def countPhotonsAgainstEnergyFunction(evt, photonscore_record, energy_record, energyFunction = lambda x : 200, outkey="photons: "):
    """A hitfinder that tests given photon score (e.g. photon count) against a predicted photon threshold
    that is dependent on some given energy and
    adds a boolean to ``evt["analysis"][outkey + "isHit"]``,  the hitscore to ``evt["analysis"][outkey + "hitscore"]`` and
    the limit to ``evt["analysis"][outkey + "photonLimit"]

    Args:
        :evt:                 The event variable
        :photonscore_record:  A :func:`~backend.Record` object containing a photon score, e.g. total photon count
        :energy_record:"      A :func:`~backend.Record` object containing an energy value, e.g. from gas monitor detector 

    Kwargs:
        :energyFunction(function with double argument): Function that computes the photon threshold, given the energy
        :outkey(str):                                   Prefix of data key of resulting :func:`~backend.Record` object, default is "photons: " 
    
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

def countPhotonsAgainstEnergyPolynomial(evt, photonscore_record, energy_record, energyPolynomial = [200], outkey="photons: "):
    """A hitfinder that tests photon score (e.g. photon count) against a predicted photon threshold
    that is dependent on some given energy and 
    adds a boolean to ``evt["analysis"][outkey + "isHit"]``,  the hitscore to ``evt["analysis"][outkey + "hitscore"]`` and
    the limit to ``evt["analysis"][outkey + "photonLimit"]

    Args:
        :evt:       The event variable
        :photonscore_record: A :func:`~backend.Record` object containting a photon score, e.g. total photon count
        :energy_record:"     A :func:`~backend.Record` object containting an energy value, e.g. from gas monitor detector 

    Kwargs:
        :energyPolynomial: array_like with polynomial coefficients fed to polyval (polynomial order one less than list length)
        :outkey(str):            Prefix of data key of resulting :func:`~backend.Record` object, default is "photons: " 
    
    :Authors:
        Carl Nettelblad (carl.nettelblad@it.uu.se)
    """
    countPhotonsAgainstEnergyFunction(evt, photonscore_record, energy_record, lambda x : np.polyval(energyPolynomial, x), outkey=outkey)

def photon_count_frame(evt,front_type_s,front_key_s,aduThreshold,outkey=""):
    photon_frame = (evt[front_type_s][front_key_s].data/aduThreshold).round()
    photon_frame[photon_frame<=0] = 0
    v = evt["analysis"]
    add_record(v, "analysis", outkey+"photon_count", photon_frame)

def lambda_values(evt,pulse_energy,sum_over_bkg_frames,fit_bkg,sample_params,outkey=""):
    frame_expected_phc = np.dot(sample_params,np.array([pulse_energy**3,pulse_energy**2,pulse_energy,1]))
    lambdav = sum_over_bkg_frames*frame_expected_phc/fit_bkg.sum()
    lambdav[lambdav<=0] = 1e-30
    v = evt["analysis"]
    add_record(v, "analysis", outkey+"lambda_values", lambdav)
    add_record(v, "analysis", outkey+"expected_phc", frame_expected_phc)

def baglivo_score(evt,poisson_mask,outkey=""):
    #poisson_mask = poisson_mask.astype(bool)
    N = evt["analysis"]["expected_phc"].data
    observed_phc = evt["analysis"]["photon_count"].data[poisson_mask]
    lambda_values = evt["analysis"]["lambda_values"].data[poisson_mask]
    normalized_lambdas = lambda_values/lambda_values.sum()

    partial_sum = observed_phc*(np.log(observed_phc) - np.log(normalized_lambdas) - np.log(N))
    partial_sum[observed_phc==0] = 0

    logval = partial_sum.sum()
     
    v = evt["analysis"]
    add_record(v, "analysis", outkey+"baglivo_score", logval)

def stat_hitfinder(evt,pulse_energy,thr_params,bag_bkg,outkey="bagscore: "):
    thr = thr_params[0]*pulse_energy + thr_params[1] + 2*bag_bkg.std()    
    hit = evt["analysis"]["baglivo_score"].data > thr
    v = evt["analysis"]
    add_record(v, "analysis", outkey+"isHit", hit)
    add_record(v, "analysis", outkey+"threshold", thr)


def generate_radial_mask(mask,cx,cy,radius):
    [dimy,dimx] = mask.shape

    x = np.arange(dimx)-cx
    y = np.arange(dimy)-cy
    X,Y = np.meshgrid(x,y)
    R = np.sqrt(X**2+Y**2)

    mask2 = mask.copy()
    mask2[R > radius] = 0
    return mask2
