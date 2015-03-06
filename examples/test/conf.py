import time
import analysis.event
import analysis.beamline
import analysis.background
import analysis.pixel_detector

state = {
    'Facility': 'dummy',
    'squareImage' : True,
}

def onEvent(evt):
    analysis.pixel_detector.plotImages(evt['photonPixelDetectors'])
    #analysis.pixel_detector.printStatistics(evt['photonPixelDetectors'])
    analysis.event.printProcessingRate(evt)
    time.sleep(1)
