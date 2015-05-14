import collections
import ipc
import numpy as np
from backend import  ureg
from backend import Record

def averagePulseEnergy(evt, pulseEnergies):
    """Expects a dictionary of pulse energy ``Records`` and adds the
    average pulse energy to ``evt["averagePulseEnergy"]``."""
    pulseEnergy = []
    for pE in pulseEnergies.values():
        if (pE.unit == ureg.mJ):
            pulseEnergy.append(pE.data)
    if not pulseEnergy:
        return
    else:
        return Record("averagePulseEnergy", np.mean(pulseEnergy), ureg.mJ)

def printPulseEnergy(pulseEnergies):
    """Expects a dictionary of pulse energy ``Records`` and prints pulse energies to screen."""
    for k,v in pulseEnergies.iteritems():
        print "%s = %s" % (k, (v.data*v.unit))

def printPhotonEnergy(photonEnergies):
    """Expects a dictionary of photon energy ``Records`` and prints photon energies to screen."""
    for k,v in photonEnergies.iteritems():
        print "%s = %s" % (k, v.data*v.unit)
