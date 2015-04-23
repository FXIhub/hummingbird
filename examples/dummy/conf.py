import time
import analysis.event
import analysis.beamline
import analysis.background
import analysis.pixel_detector
import ipc
import numpy
from backend import ureg

state = {
    'Facility': 'Dummy',

    'Dummy': {
        'Repetition Rate' : 1,
        'Data Sources': {
            'CCD': {
                'data': lambda: numpy.random.rand(256,128),
                'unit': ureg.ADU,                                       
                'type': 'photonPixelDetectors'
            }
        }        
    }
}

def onEvent(evt):
    ipc.broadcast.init_data('CCD', xmin=10,ymin=10)
    analysis.pixel_detector.plotImages(evt['photonPixelDetectors'])
    analysis.event.printProcessingRate(evt)
