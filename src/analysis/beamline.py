import collections
import ipc

def printPulseEnergy(pulseEnergies):
    for k,v in pulseEnergies.iteritems():
        print "%s = %s" % (k, (v.data*v.unit))

def printPhotonEnergy(photonEnergies):
    for k,v in photonEnergies.iteritems():
        print "%s = %s" % (k, v.data*v.unit)

pulseEnergiesDeques = {}
def plotPulseEnergy(pulseEnergies):
    history_length = 100
    for k,v in pulseEnergies.iteritems():
        if(k not in pulseEnergiesDeques):
            pulseEnergiesDeques[k] = collections.deque([],history_length)
        pulseEnergiesDeques[k].append(v.data)
        ipc.new_data(k, v.data)
    
