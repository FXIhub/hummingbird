import analysis.event
import analysis.beamline
import plotting.line
import time

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
    analysis.event.printID(evt['eventID'])
    plotting.line.plotHistory(evt["parameters"]["yag4_y"])
    time.sleep(2)


