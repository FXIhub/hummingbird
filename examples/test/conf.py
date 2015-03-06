import time
import analysis.event
import analysis.beamline
import analysis.background
import analysis.pixel_detector
import ipc

state = {
    'Facility': 'dummy',
    'squareImage' : True,
}

def onEvent(evt):
    ipc.broadcast.init_data('CCD', xmin=10,ymin=10, xmax=20,ymax=30)
    analysis.pixel_detector.plotImages(evt['photonPixelDetectors'])
    analysis.beamline.plotPulseEnergy(evt['pulseEnergies'])
    #analysis.pixel_detector.printStatistics(evt['photonPixelDetectors'])
    analysis.event.printProcessingRate(evt)
    time.sleep(1)
