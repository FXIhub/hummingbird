# Import analysis/plotting/simulation modules
import analysis.event
import analysis.hitfinding
import plotting.image
import plotting.line
import simulation.base

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

    # Simple hit finding (counting the number of lit pixels)
    analysis.hitfinding.countLitPixels(evt, "photonPixelDetectors", "CCD", aduThreshold=10, hitscoreThreshold=100)

    # Extract boolean (hit or miss)
    hit = evt["analysis"]["isHit - CCD"].data
    
    # Compute the hitrate
    analysis.hitfinding.hitrate(evt, hit, history=1000)
    
    # Plot the hitscore
    plotting.line.plotHistory(evt["analysis"]["hitscore - CCD"], label='Nr. of lit pixels')

    # Plot the hitrate
    plotting.line.plotHistory(evt["analysis"]["hitrate"], label='Hit rate [%]')
     
    # Visualize detector image of hits
    if hit:
        plotting.image.plotImage(evt["photonPixelDetectors"]["CCD"], vmin=-10, vmax=40)
