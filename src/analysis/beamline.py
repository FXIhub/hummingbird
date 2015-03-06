import collections
import ipc
import numpy
from backend import  ureg

def printPulseEnergy(pulseEnergies):
    for k,v in pulseEnergies.iteritems():
        print "%s = %s" % (k, (v.data*v.unit))

def printPhotonEnergy(photonEnergies):
    for k,v in photonEnergies.iteritems():
        print "%s = %s" % (k, v.data*v.unit)

def plotPulseEnergy(pulseEnergies):
    for k,v in pulseEnergies.iteritems():
        ipc.new_data(k, v.data)

def averagePulseEnergies(pulseEnergies):
    pulseEnergy = []
    for pE in pulseEnergies.values():
        if (pE.unit == ureg.mJ):
            pulseEnergy.append(pE.data)
    if pulseEnergy:
        return numpy.mean(pulseEnergy)
    else:
        return 0
