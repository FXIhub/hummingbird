
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
    'Repetition Rate' : 20,
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

    # Simple hit finding (counting the number of lit pixels)
    analysis.hitfinding.countLitPixels(evt, evt["photonPixelDetectors"]["CCD"], aduThreshold=10, hitscoreThreshold=100)

    # Extract boolean (hit or miss)
    hit = evt["analysis"]["litpixel: isHit"].data
    
    # Compute the hitrate
    analysis.hitfinding.hitrate(evt, hit, history=5000)
    
    # Plot the hitscore
    plotting.line.plotHistory(evt["analysis"]["litpixel: hitscore"], label='Nr. of lit pixels', hline=100, group="A")

    # Plot the hitrate
    plotting.line.plotHistory(evt["analysis"]["hitrate"], label='Hit rate [%]', group="B")
     
    # Visualize detector image of hits
    if hit:
        plotting.image.plotImage(evt["photonPixelDetectors"]["CCD"], vmin=-10, vmax=40, group="Detectors")
