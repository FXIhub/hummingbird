import collections
import ipc
import numpy as np
from backend import  ureg
from backend import Record

def averagePulseEnergy(pulseEnergies):
    """Returns the average pulse energy    
    Args:
        :pulseEnergies(dict(Record)): A dictionary of pulseEnergy records.
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

def printPulseEnergy(pulseEnergies):
    """Prints pulse energies to screen
    Args:
        :pulseEnergies(dict(Record)): A dictionary of pulseEnergy records.
    """
    for k,v in pulseEnergies.iteritems():
        print "%s = %s" % (k, (v.data*v.unit))

def printPhotonEnergy(photonEnergies):
    """Prints photon energues to screen
    Args:
        :photonEnergies(dict(Record)): A dictionary of photonEnergy records.
    """
    for k,v in photonEnergies.iteritems():
        print "%s = %s" % (k, v.data*v.unit)
