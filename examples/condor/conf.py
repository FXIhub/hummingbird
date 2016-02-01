import simulation.condor
import analysis.event
import plotting.image
import os

# Absolute path to the location of the example
__thisdir__ = os.path.dirname(os.path.realpath(__file__))


sim = simulation.condor.Simulation(__thisdir__ + "/virus.conf")
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
