def printPulseEnergy(evt):
    pulseEnergies = evt['pulseEnergy']
    for k,v in pulseEnergies.iteritems():
        # Convert from J to mJ
        print "%s = %f mJ" % (k, v*1000.0)

def printPhotonEnergy(evt):
    photonEnergies = evt['photonEnergy']
    for p in photonEnergies.keys():
        # Convert from J to eV
        print "%s = %f eV" % (p, photonEnergies[p]*6.242e18)
    
