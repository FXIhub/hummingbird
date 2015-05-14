import time
import numpy

from backend import ureg
import ipc
import simulation.simple
import analysis.event
import analysis.beamline
import analysis.background
import analysis.pixel_detector
import plotting.image
import plotting.line
import plotting.correlation

sim = simulation.simple.Simulation("examples/simulation/condor.conf")

state = {
    'Facility': 'Dummy',

    'Dummy': {
        'Repetition Rate' : 10,
        'Simulation': sim,
        'Data Sources': {
            'CCD': {
                'data': sim.get_pattern,
                'unit': ureg.ph,     
                'type': 'photonPixelDetectors'
            },
            'inj_x': {
                'data': sim.get_position_x,
                'unit': ureg.m,
                'type': 'parameters'
            },
            'intensity': {
                'data': sim.get_intensity,
                'unit': None,
                'type': 'parameters'
            },
            'particle_size': {
                'data': sim.get_particle_size,
                'unit': ureg.nm,
                'type': 'parameters'
            }
        }        
    }
}

def onEvent(evt):
    ipc.broadcast.init_data('CCD', xmin=10,ymin=10)
    for k,v in evt['photonPixelDetectors'].iteritems():
        plotting.image.plotImage(v)
    plotting.line.plotHistory(evt["parameters"]["inj_x"])
    plotting.line.plotHistory(evt["parameters"]["intensity"])
    plotting.line.plotHistory(evt["parameters"]["particle_size"])
    #plotting.correlation.plotHeatmap(evt["parameters"]["particle_size"], evt["parameters"]["intensity"], xmin=30e-9, xmax=90e-9, xbins=60)
    analysis.event.printProcessingRate()
    analysis.event.printKeys(evt)
