import time
import analysis.event
import analysis.beamline
import analysis.pixel_detector

state = {
    'Facility': 'dummy'
}

def onEvent(evt):
    analysis.beamline.plotPulseEnergy(evt['pulseEnergies'])
    analysis.pixel_detector.plotImages(evt['photonPixelDetectors'])
    analysis.event.printProcessingRate(evt)
    time.sleep(1)
