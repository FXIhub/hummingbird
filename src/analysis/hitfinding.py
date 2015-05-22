import ipc
from backend import Record
import numpy as np
import collections

counter = collections.deque([])
def countHits(evt, hit, history=100):
    """Takes a boolean (True for hit, False for miss) and adds accumulated nr. of hits to ``evt["nrHit"]`` and 
    accumulated nr. of misses to ``evt["nrMiss"]``"""
    global counter
    if counter.maxlen is None or (counter.maxlen is not history):
        counter = collections.deque([], history)
    if hit: counter.append(True)
    else: counter.append(False)
    evt["nrHit"]  = Record("nrHit",  counter.count(True))
    evt["nrMiss"] = Record("nrMiss", counter.count(False))

def hitrate(evt, hit, *kwargs):
    """Takes a boolean (True for hit, False for miss) and adds the hit rate in % to ``evt["hitrate"]`` if called by main worker, otherwise it returns None. Has been tested in MPI mode"""
    countHits(evt, hit, *kwargs)
    hitrate = np.array(100 * evt["nrHit"].data / float(evt["nrHit"].data + evt["nrMiss"].data))
    ipc.mpi.sum(hitrate)
    if(ipc.mpi.is_main_worker()):
        evt["hitrate"] = Record("hitrate", hitrate[()]/ipc.mpi.size, unit='%')
    else:
        evt["hitrate"] = None

def countLitPixels(evt, detector, aduThreshold=20, hitscoreThreshold=200):
    """A simple hitfinder. Takes a detector ``Record``, counts the number of lit pixels and
    adds a boolean to ``evt["isHit"]`` and  the hitscore to ``evt["hitscore - " + detector.name]``.

    Args:
        :detector(Record):       Hitfinding is based on detector.data
    Kwargs:
        :aduThreshold(int):      only pixels above this threshold (in ADUs) are valid, default=20
        :hitscoreThreshold(int): events with hitscore (Nr. of lit pixels)  above this threshold are hits, default=200
    """
    hitscore = (detector.data > aduThreshold).sum()
    evt["isHit"] = hitscore > hitscoreThreshold
    evt["hitscore - " + detector.name] = Record("hitscore - " + detector.name, hitscore)
