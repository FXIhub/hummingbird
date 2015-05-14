import ipc
from backend import Record
import numpy as np


counter = []
def countHits(evt, hit):
    """Takes a boolean (True for hit, False for miss) and adds accumulated nr. of hits to ``evt["nrHit"]`` and 
    accumulated nr. of misses to ``evt["nrMiss"]``"""
    if hit: counter.append(True)
    else: counter.append(False)
    evt["nrHit"]  = Record("nrHit",  sum(counter))
    evt["nrMiss"] = Record("nrMiss", len(counter) - sum(counter))

def countLitPixels(evt, detector, aduThreshold=20, litPixelThreshold=200):
    """A simple hitfinder. Takes a detector ``Record``, counts the number of lit pixels and
    adds a boolean to ``evt["isHit"]`` and  the hitscore to ``evt["hitscore - " + detector.name]``.

    Args:
        :detector(Record):       Hitfinding is based on detector.data
    Kwargs:
        :aduThreshold(int):      only pixels above this threshold (in ADUs) are valid, default=20
        :litPixelThreshold(int): events with lit pixels above this threshold are hits, default=200
    """
    hitscore = (detector.data > aduThreshold).sum()
    evt["isHit"] = hitscore > litPixelThreshold
    evt["hitscore - " + detector.name] = Record("hitscore - " + detector.name, hitscore)
