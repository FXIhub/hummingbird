def printPulseEnergy(pulseEnergies):
    for k,v in pulseEnergies.iteritems():
        print "%s = %s" % (k, (v.data*v.unit))

def printPhotonEnergy(photonEnergies):
    for k,v in photonEnergies.iteritems():
        print "%s = %s" % (k, v.data*v.unit)
    
