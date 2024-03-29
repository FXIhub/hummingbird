import time

from hummingbird import analysis, plotting

state = {
    'Facility': 'LCLS',
    'LCLS/DataSource': 'exp=XCS/xcstut13:run=15'
}

def onEvent(evt):
    analysis.event.printKeys(evt)
    analysis.event.printNativeKeys(evt)
    analysis.beamline.printPulseEnergy(evt['pulseEnergies'])
    analysis.beamline.printPhotonEnergy(evt['photonEnergies'])
    analysis.event.printProcessingRate()
    print evt['eventID'].keys()
    print evt['pulseEnergies'].keys()
    print evt['photonEnergies'].keys()
    print evt['eventCodes'].keys()
    print evt['parameters'].keys()
    print evt['analysis'].keys()
    plotting.line.plotHistory(evt["parameters"]["yag4_y"])
    time.sleep(2)


