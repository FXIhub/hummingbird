import time
import analysis.event
import analysis.beamline
import analysis.pixel_detector

state = {
    'Facility': 'dummy'
}

def onEvent(evt):
    analysis.beamline.plotPulseEnergy(evt['pulseEnergies'])
    analysis.event.printProcessingRate(evt)
    time.sleep(1)
