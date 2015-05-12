import ipc
from backend import Record
import numpy as np


counter = []
def countHits(hit):
    """Counting hits and blanks

    Args:
        :hit(bool): Hit or blank
    Returns:
        :A tuple of records, nrHits and nrBlanks
    """
    if hit: counter.append(True)
    else: counter.append(False)
    return Record("nrHits", sum(counter)), Record("nrBlanks", len(counter) - sum(counter))

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
