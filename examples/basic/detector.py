# Import analysis/plotting/simulation modules
import analysis.event
import analysis.pixel_detector
import plotting.line
import plotting.image
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

# Configuration for histogram plot
histogramCCD = {
    'hmin': -10,
    'hmax': 100,
    'bins': 200,
    'label': "Nr of photons",
    'history': 200}

# This function is called for every single event
# following the given recipy of analysis
def onEvent(evt):

    # Processing rate [Hz]
    analysis.event.printProcessingRate()

    # Detector statistics
    analysis.pixel_detector.printStatistics(evt["photonPixelDetectors"])

    # Count Nr. of Photons
    analysis.pixel_detector.totalNrPhotons(evt, "photonPixelDetectors", "CCD")
    plotting.line.plotHistory(evt["analysis"]["nrPhotons - CCD"], label='Nr of photons / frame', history=50)

    # Detector histogram
    plotting.line.plotHistogram(evt["photonPixelDetectors"]["CCD"], **histogramCCD)
 
    # Detector images
    plotting.image.plotImage(evt["photonPixelDetectors"]["CCD"])
