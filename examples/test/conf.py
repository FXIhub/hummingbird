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
#    ipc.broadcast.init_data('CCD', xmin=10,ymin=10, xmax=20,ymax=30, xlabel='foo', ylabel='bar')

    t0 = time.time()
    ipc.new_data('CCD2', evt['photonPixelDetectors']['CCD2'].data)
    ipc.new_data('CCD', evt['photonPixelDetectors']['CCD'].data.T, foo='bar')
    t1 = time.time()
    print 1.0/(t1-t0)
#    analysis.pixel_detector.plotImages(evt['photonPixelDetectors'])
    ipc.broadcast.init_data('pulseEnergy1', xlabel='foo', ylabel='bar2', history_length=3)
    analysis.beamline.plotPulseEnergy(evt['pulseEnergies'])
    #analysis.pixel_detector.printStatistics(evt['photonPixelDetectors'])
    analysis.event.printProcessingRate(evt)
    time.sleep(1)
