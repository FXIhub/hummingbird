import simulation.simple
import analysis.event
import analysis.pixel_detector
import plotting.line
import plotting.image

sim = simulation.simple.Simulation("examples/detector/virus.conf")
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

# Configure plots
# ---------------
histogramCCD = {
    'hmin': -1,
    'hmax': 19,
    'bins': 100,
    'label': "Nr of photons",
    'history': 50}

def onEvent(evt):

    # Processing rate
    analysis.event.printProcessingRate()

    # Available datasets
    analysis.event.printKeys(evt)
    analysis.event.printKeys(evt, "parameters")

    # Detector statistics
    analysis.pixel_detector.printStatistics(evt["photonPixelDetectors"])

    # Count Nr. of Photons
    analysis.pixel_detector.totalNrPhotons(evt, evt["photonPixelDetectors"]["CCD"])
    plotting.line.plotHistory(evt["nrPhotons - CCD"], label='Nr of photons / frame', history=50)

    # Detector histogram
    plotting.line.plotHistogram(evt["photonPixelDetectors"]["CCD"], **histogramCCD)
 
    # Detector images
    plotting.image.plotImage(evt["photonPixelDetectors"]["CCD"])
