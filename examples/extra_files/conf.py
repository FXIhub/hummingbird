import simulation.simple
import analysis.event
import analysis.pixel_detector
import analysis.hitfinding
import plotting.line
import plotting.image
import utils.reader

sim = simulation.simple.Simulation("examples/extra_files/virus.conf")
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


# Reading mask
# ------------
mreader = utils.reader.MaskReader('examples/extra_files/mask.h5', 'data/data')

# Reading geometry
# ----------------
greader = utils.reader.GeometryReader('examples/extra_files/geometry.h5')

# Reading something else
# ----------------------
#reader = utils.reader.H5Reader('examples/extra_files/something.h5', 'somekey')

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

    # Assemble images (apply geometry)
    analysis.pixel_detector.assemble(evt, "photonPixelDetectors", "CCD", \
                                     greader.x, greader.y, nx=414, ny=414, outkey="CCD")
    
    # Count Nr. of Photons
    analysis.pixel_detector.totalNrPhotons(evt,"analysis", "CCD")
    plotting.line.plotHistory(evt["analysis"]["nrPhotons - CCD"], label='Nr of photons / frame', history=50)

    # Simple hitfinding (Count Nr. of lit pixels)
    analysis.hitfinding.countLitPixels(evt, "analysis", "CCD", \
                                       aduThreshold=0.5, hitscoreThreshold=10, mask=mreader.boolean_mask)

    # Compute the hitrate
    analysis.hitfinding.hitrate(evt, evt["analysis"]["isHit - CCD"], history=100)
    
    # Plot the hitscore
    plotting.line.plotHistory(evt["analysis"]["hitscore - CCD"], label='Nr. of lit pixels')

    # Plot the hitrate
    plotting.line.plotHistory(evt["analysis"]["hitrate"], label='Hit rate [%]')
    
    # Plot hit images
    if evt["analysis"]["isHit - CCD"]:
        plotting.image.plotImage(evt["analysis"]["CCD"], mask=mreader.integer_mask)
