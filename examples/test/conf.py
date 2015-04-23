import time
import analysis.event
import analysis.beamline
import analysis.background
import analysis.pixel_detector
import ipc
import random
from backend import ureg
import numpy

state = {
    'Facility': 'dummy',
    'squareImage' : True,
    'Dummy': {
        'Repetition Rate' : 1,
        'Data Sources': {
            'CCD': {
                'data': lambda: numpy.random.rand(256,128),
                'unit': ureg.ADU,     
                'type': 'photonPixelDetectors'
            },
            'CCD1': {
                'data': lambda: numpy.random.rand(64,64),
                'unit': ureg.ADU,     
                'type': 'photonPixelDetectors'
            },
            'tof': {
                'data': lambda: numpy.random.rand(256),
                'unit': ureg.mJ,
                'type': 'ionTOFs'
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

    ipc.new_data('CCD', evt['photonPixelDetectors']['CCD'].data, xlabel='x', ylabel='y', xmax=112.0, xmin=100, ymin=-50)
    ipc.new_data('CCD_flipped', evt['photonPixelDetectors']['CCD'].data, flipy=True, xlabel='x', ylabel='y', xmax=112.0, xmin=100, ymin=-50)
    ipc.new_data('CCD_tranposed', evt['photonPixelDetectors']['CCD'].data, transpose=True, xlabel='x', ylabel='y', xmax=112.0, xmin=100, ymin=-50)
    ipc.new_data('CCD_noisy', evt['photonPixelDetectors']['CCD1'].data)
    ipc.new_data('tof', evt['ionTOFs']['tof'].data, xlabel='foo')
    ipc.broadcast.init_data('pulseEnergy1', xlabel='foo', ylabel='bar2', history_length=3)
    ipc.new_data('pulse1', evt['pulseEnergies']['pulseEnergy1'].data)
    ipc.new_data('pulse3', evt['pulseEnergies']['pulseEnergy1'].data, xlabel='foo')
    analysis.event.printProcessingRate(evt)
