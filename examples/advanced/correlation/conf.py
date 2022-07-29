import simulation.condor
import analysis.event
import analysis.pixel_detector
import analysis.hitfinding
import plotting.line
import plotting.image
import plotting.correlation
import numpy as np

sim = simulation.condor.Simulation("examples/advanced/correlation/virus.conf")
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
            'injector_x': {
                'data': lambda: np.random.random()*1e-6,
                'unit': 'nm',
                'type': 'parameters'
            },
            'injector_y': {
                'data': lambda: np.random.random()*1e-6,
                'unit': 'nm',
                'type': 'parameters'
            },
            'injector_z': {
                'data': lambda: np.random.random()*1e-6,
                'unit': 'nm',
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

hitrateMeanMap = {
    'xmin': -1000,
    'xmax': +1000,
    'ymin': -1000,
    'ymax': +1000,
    'xbins': 10,
    'ybins': 10}
    
def onEvent(evt):

    # Processing rate
    analysis.event.printProcessingRate()

    # Detector statistics
    analysis.pixel_detector.printStatistics(evt["photonPixelDetectors"])

    # Count Nr. of Photons
    analysis.pixel_detector.totalNrPhotons(evt,evt["photonPixelDetectors"]["CCD"], outkey="nrPhotons - CCD")
    plotting.line.plotHistory(evt["analysis"]["nrPhotons - CCD"], label='Nr of photons / frame', history=50)

    # Simple hitfinding (Count Nr. of lit pixels)
    analysis.hitfinding.countLitPixels(evt, evt["photonPixelDetectors"]["CCD"], aduThreshold=0.5, hitscoreThreshold=10)

    # Compute the hitrate
    analysis.hitfinding.hitrate(evt, evt["analysis"]["litpixel: isHit"], history=100)
    
    # Plot the hitscore
    plotting.line.plotHistory(evt["analysis"]["litpixel: hitscore"], label='Nr. of lit pixels')

    # Plot the hitrate
    plotting.line.plotHistory(evt["analysis"]["hitrate"], label='Hit rate [%]')
     
    # Plot hit images
    if evt["analysis"]["litpixel: isHit"]:
        plotting.image.plotImage(evt["photonPixelDetectors"]["CCD"])

    # Plot MeanMap of hitrate(x,y)
    x = evt["parameters"]["injector_x"]
    y = evt["parameters"]["injector_y"]
    z = evt["analysis"]["litpixel: isHit"]
    plotting.correlation.plotMeanMap(x,y,z, name='HitrateMeanMap', **hitrateMeanMap)

    # Scatter plot of Hitscore vs. Nr. scattered photons
    x = evt["analysis"]["litpixel: hitscore"]
    y = evt["analysis"]["nrPhotons - CCD"]
    plotting.correlation.plotScatter(x,y, history=1000) 

    # Scatter plot of injector X vs. injector Y with color-coded hitrate
    x = evt["parameters"]["injector_x"]
    y = evt["parameters"]["injector_y"]
    z = evt["analysis"]["nrPhotons - CCD"]
    plotting.correlation.plotScatterColor(x,y,z, history=100, vmin=0, vmax=5000, zlabel='Nr. of Photons')
