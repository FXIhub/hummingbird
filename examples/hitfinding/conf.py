import simulation.simple
import analysis.event
import analysis.pixel_detector
import analysis.hitfinding
import plotting.line
import plotting.image

sim = simulation.simple.Simulation("examples/hitfinding/virus.conf")
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

    # Detector statistics
    analysis.pixel_detector.printStatistics(evt["photonPixelDetectors"])

    # Count Nr. of Photons
    analysis.pixel_detector.totalNrPhotons(evt, evt["photonPixelDetectors"]["CCD"])
    plotting.line.plotHistory(evt["nrPhotons - CCD"], label='Nr of photons / frame', history=50)

    # Simple hitfinding (Count Nr. of lit pixels)
    analysis.hitfinding.countLitPixels(evt, evt["photonPixelDetectors"]["CCD"], aduThreshold=0.5, hitscoreThreshold=10)

    # Compute the hitrate
    analysis.hitfinding.hitrate(evt, evt["isHit"])
    
    # Plot the hitscore
    plotting.line.plotHistory(evt["hitscore - CCD"], label='Nr. of lit pixels')

    # Plot the hitrate
    plotting.line.plotHistory(evt["hitrate"], label='Hit rate [%]')
     
    # Plot hit images
    if evt["isHit"]:
        plotting.image.plotImage(evt["photonPixelDetectors"]["CCD"])
