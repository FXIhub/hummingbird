import collections
import ipc
import numpy as np
from backend import  ureg
from backend import Record

def printPulseEnergy(pulseEnergies):
    for k,v in pulseEnergies.iteritems():
        print "%s = %s" % (k, (v.data*v.unit))

def printPhotonEnergy(photonEnergies):
    for k,v in photonEnergies.iteritems():
        print "%s = %s" % (k, v.data*v.unit)

def averagePulseEnergy(pulseEnergies):
    """returns the average pulse energy    
    Args:
        :pulseEnergies(dict(Record)): A dictionary of pulse energies
    Returns:
        Record average
    """
    pulseEnergy = []
    for pE in pulseEnergies.values():
        if (pE.unit == ureg.mJ):
            pulseEnergy.append(pE.data)
    if not pulseEnergy:
        return
    else:
        return Record("averagePulseEnergy", np.mean(pulseEnergy), ureg.mJ)
