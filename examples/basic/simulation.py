# Import analysis/plotting/simulation modules
from hummingbird import analysis, plotting, simulation

# Simulate diffraction data  
sim = simulation.base.Simulation()
sim.hitrate = 0.5
sim.sigma = 1

# Specify the facility
state = {}
state['Facility'] = 'Dummy'

# Create a dummy facility
state['Dummy'] = {
    # The event repetition rate of the dummy facility [Hz]
    'Repetition Rate' : 10,
    # Specify simulation
    'Simulation': sim,
    # Dictionary of data sources
    'Data Sources': {
        # Data from a virtual diffraction detector
        'CCD': {
            # Fetch diffraction data from the simulation
            'data': sim.get_pattern,
            'unit': 'ADU',
            'type': 'photonPixelDetectors'
        }
    }
}

# This function is called for every single event
# following the given recipy of analysis
def onEvent(evt):

    # Processing rate [Hz]
    analysis.event.printProcessingRate()

    # Visualize detector image
    plotting.image.plotImage(evt['photonPixelDetectors']['CCD'], vmin=-10, vmax=40)
