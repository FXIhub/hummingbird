from hummingbird import analysis, plotting, simulation, utils

sim = simulation.condor.Simulation("examples/advanced/extra_files/virus.conf")
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


# Reading mask
# ------------
mreader = utils.reader.MaskReader('examples/advanced/extra_files/mask.h5', 'data/data')

# Reading geometry
# ----------------
greader = utils.reader.GeometryReader('examples/advanced/extra_files/geometry.h5')

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
    analysis.pixel_detector.totalNrPhotons(evt,evt["analysis"]["CCD"],outkey='nrPhotons - CCD')
    plotting.line.plotHistory(evt["analysis"]["nrPhotons - CCD"], label='Nr of photons / frame', history=50)

    # Simple hitfinding (Count Nr. of lit pixels)
    analysis.hitfinding.countLitPixels(evt, evt["analysis"]["CCD"], aduThreshold=0.5, hitscoreThreshold=10, mask=mreader.boolean_mask)

    # Compute the hitrate
    analysis.hitfinding.hitrate(evt, evt["analysis"]["litpixel: isHit"], history=100)
    
    # Plot the hitscore
    plotting.line.plotHistory(evt["analysis"]["litpixel: hitscore"], label='Nr. of lit pixels')

    # Plot the hitrate
    plotting.line.plotHistory(evt["analysis"]["hitrate"], label='Hit rate [%]')
    
    # Plot hit images
    if evt["analysis"]["litpixel: isHit"]:
        plotting.image.plotImage(evt["analysis"]["CCD"], mask=mreader.integer_mask)
