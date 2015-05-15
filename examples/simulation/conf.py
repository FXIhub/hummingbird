import simulation.simple
import analysis.event
import analysis.beamline
import analysis.background
import analysis.pixel_detector
import plotting.image
import plotting.line
import plotting.correlation

sim = simulation.simple.Simulation("examples/simulation/virus.conf")
sim.reprate = 120.
sim.hitrate = 0.1

state = {
    'Facility': 'Dummy',

    'Dummy': {
        'Repetition Rate' : 120,
        'Simulation': sim,
        'Data Sources': {
            'CCD': {
                'data': sim.get_pattern,
                'unit': 'ph',
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
