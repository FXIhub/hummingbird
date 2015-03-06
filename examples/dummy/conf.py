import time
import analysis.event
import analysis.beamline
import analysis.background
import analysis.pixel_detector

state = {
    'Facility': 'dummy',
    'squareImage' : True,

    'aduThreshold': 10,
    'aduPhoton':    30,

    'meanPhotonMap/initialize': True,
    'meanPhotonMap/paramXmin': -2,
    'meanPhotonMap/paramXmax':  2,
    'meanPhotonMap/paramYmin': -2,
    'meanPhotonMap/paramYmax':  2,
    'meanPhotonMap/paramXbin':  0.01,
    'meanPhotonMap/paramYbin':  0.01,
    'meanPhotonMap/updateRate': 100
}

def onEvent(evt):
    #nrPhotons = analysis.pixel_detector.countNrPhotons(evt['photonPixelDetectors']['CCD'].data)
    #analysis.background.plotMeanPhotonMap(nrPhotons, evt['parameters']['apertureX'].data, evt['parameters']['apertureY'].data)    
    #print "Available keys: ", evt.keys()

    analysis.pixel_detector.plotImages(evt['photonPixelDetectors'])
    #analysis.pixel_detector.printStatistics(evt['photonPixelDetectors'])
    analysis.event.printProcessingRate(evt)
    time.sleep(0.1)
