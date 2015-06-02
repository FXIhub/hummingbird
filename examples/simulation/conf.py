import simulation.simple
import analysis.event

sim = simulation.simple.Simulation("examples/simulation/virus.conf")
sim.hitrate = 0.1

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
