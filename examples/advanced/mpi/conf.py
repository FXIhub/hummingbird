import random
import time

import numpy

from hummingbird import analysis, ipc

numpy.random.seed()

state = {
    'Facility': 'dummy',
    'squareImage' : True,
    'Dummy': {
        'Repetition Rate' : 10,
        'Data Sources': {
            'CCD': {
                'data': lambda: numpy.random.rand(256,128),
                'unit': 'ADU',     
                'type': 'photonPixelDetectors'
            },
            'CCD1': {
                'data': lambda: numpy.random.rand(64,64),
                'unit': 'ADU',     
                'type': 'photonPixelDetectors'
            },
            'tof': {
                'data': lambda: numpy.random.rand(2,256),
                'unit': 'mJ',
                'type': 'ionTOFs'
            },
            'pulseEnergy1': {
                'data': lambda: random.random(),
                'unit': 'mJ',
                'type': 'pulseEnergies'
            }
        }        
    }
}


def onEvent(evt):
    analysis.event.printProcessingRate()
    ipc.new_data("TOF", evt["ionTOFs"]["tof"].data)
    if numpy.random.randint(100) == 0:
        time.sleep(1)
