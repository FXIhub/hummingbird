import os

import simulation.simple
import analysis.event
import plotting.image

here = os.path.dirname(os.path.realpath(__file__))

sim = simulation.simple.Simulation(here + "/virus.conf")
sim.hitrate = 0.9

state = {
    'Facility': 'Dummy',

    'Dummy': {
        'Repetition Rate' : 1,
        'Simulation': sim,
        'Data Sources': {
            'CCD': {
                'data': sim.get_pattern,
                'unit': 'count',
                'type': 'photonPixelDetectors'
            },
            'pulseEnergy': {
                'data': sim.get_pulse_energy,
                'unit': 'J',
                'type': 'pulseEnergies'
            }
        }        
    }
}

def onEvent(evt):

    # Processing rate
    analysis.event.printProcessingRate()

    # Available datasets
    analysis.event.printKeys(evt)

    plotting.image.plotImage(evt['photonPixelDetectors']['CCD'])
