import time
import analysis.event
import ipc
import random
from backend import ureg
import numpy

state = {
    'Facility': 'dummy',
    'Dummy': {
        'Repetition Rate' : 1,
        'Data Sources': {
            'CCD': {
                'data': lambda: numpy.random.rand(256,128),
                'unit': ureg.ADU,     
                'type': 'photonPixelDetectors'
            },
            'pulseEnergy1': {
                'data': lambda: random.random(),
                'unit': ureg.mJ,
                'type': 'pulseEnergies'
            }
        }        
    }
}

def onEvent(evt):
    analysis.event.printKeys(evt)
    print evt['photonPixelDetectors'].keys()
    ipc.new_data('CCD', evt['photonPixelDetectors']['CCD'].data)
    ipc.new_data('pulse1', evt['pulseEnergies']['pulseEnergy1'].data)
    analysis.event.printProcessingRate(evt)
