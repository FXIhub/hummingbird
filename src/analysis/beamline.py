def printPulseEnergy(evt):
    pulseEnergies = evt['pulseEnergy']
    for p in pulseEnergies:
        # Convert from J to mJ
        print "%s = %f mJ" % (p['desc'], p['data']*1000.0)

def printPhotonEnergy(evt):
    photonEnergies = evt['photonEnergy']
    for p in photonEnergies:
        # Convert from J to eV
        print "%s = %f eV" % (p['desc'], p['data']*6.242e18)
    
