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
            },
            'inj_x': {
                'data': sim.get_position_x,
                'unit': 'm',
                'type': 'parameters'
            },
            'inj_y': {
                'data': sim.get_position_y,
                'unit': 'm',
                'type': 'parameters'
            },
            'inj_z': {
                'data': sim.get_position_z,
                'unit': 'm',
                'type': 'parameters'
            }
        }        
    }
}

def onEvent(evt):
    analysis.event.printProcessingRate()
    analysis.event.printKeys(evt)
    analysis.event.printKeys(evt, "parameters")
