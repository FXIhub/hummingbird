import os
import time
import utils.reader
import simulation.simple
import analysis.event
import analysis.pixel_detector
import analysis.hitfinding
import analysis.sizing
import plotting.line
import plotting.image
from backend import ureg

sim = simulation.simple.Simulation("examples/sizing/virus.conf")
sim.hitrate = 0.1

state = {
    'Facility': 'Dummy',

    'Dummy': {
        'Repetition Rate' : 1,
        'Simulation': sim,
        'Data Sources': {
            'CCD': {
                'data': sim.get_pattern,
                'unit': '',
                'type': 'photonPixelDetectors'
            },
            'pulseEnergy': {
                'data': sim.get_pulse_energy,
                'unit': 'J',
                'type': 'pulseEnergies'
            },
            'diameter': {
                'data': sim.get_particle_diameter_nm,
                'unit': 'nm',
                'type': 'parameters'
            },
            'intensity': {
                'data': sim.get_intensity_mJ_um2,
                'unit': "mJ/um**2",
                'type': 'parameters'
            },
           'offCenterX': {
               'data': sim.get_offCenterX,
               'unit': '',
               'type': 'parameters'
            },
           'offCenterY': {
               'data': sim.get_offCenterY,
               'unit': '',
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

# Model parameters for sphere
# ---------------------------
modelParams = {
    'wavelength':0.12398,
    'pixelsize':110,
    'distance':2160,
    'adu_per_photon':1,
    'quantum_efficiency':1.,
    'material':'virus'}

# Sizing parameters
# -----------------
sizingParams = {
    'd0':100,
    'i0':1,
    'mask_radius':100,
    'downsampling':1,
    'brute_evals':10,
    'photon_counting':True}

this_dir = os.path.dirname(os.path.realpath(__file__))
mask = utils.reader.MaskReader(this_dir + "/mask.h5","/data/data").boolean_mask
    
def onEvent(evt):

    # Processing rate
    analysis.event.printProcessingRate()

    # Detector statistics
    analysis.pixel_detector.printStatistics(evt["photonPixelDetectors"])

    # Count Nr. of Photons
    analysis.pixel_detector.totalNrPhotons(evt,"photonPixelDetectors", "CCD")
    plotting.line.plotHistory(evt["analysis"]["nrPhotons - CCD"], label='Nr of photons / frame', history=50)

    # Simple hitfinding (Count Nr. of lit pixels)
    analysis.hitfinding.countLitPixels(evt, "photonPixelDetectors", "CCD", aduThreshold=0.5, hitscoreThreshold=10)

    # Compute the hitrate
    analysis.hitfinding.hitrate(evt, evt["analysis"]["isHit - CCD"], history=500)
    
    # Plot the hitscore
    plotting.line.plotHistory(evt["analysis"]["hitscore - CCD"], label='Nr. of lit pixels')

    # Plot the hitrate
    plotting.line.plotHistory(evt["analysis"]["hitrate"], label='Hit rate [%]')
    
    # Perform sizing on hits
    if evt["analysis"]["isHit - CCD"]:

        print "It's a hit"

        t0 = time.time()
        # Find the center of diffraction
        analysis.sizing.findCenter(evt, "photonPixelDetectors", "CCD", mask=mask, maxshift=20, threshold=0.5, blur=4)
        t_center = time.time()-t0
        
        # Fitting sphere model to get size and intensity
        t0 = time.time()
        analysis.sizing.fitSphere(evt, "photonPixelDetectors", "CCD", mask=mask, **dict(modelParams, **sizingParams))
        t_size = time.time()-t0

        # Fitting model
        t0 = time.time()
        analysis.sizing.sphereModel(evt, "analysis", "offCenterX", "offCenterY", "diameter", "intensity", (sim.ny,sim.nx), poisson=True, **modelParams)
        t_full = time.time()-t0

        t_all = t_center + t_size + t_full
        print "Time: %e sec (center / size / full : %.2f%% / %.2f%% / %.2f%%)" % (t_all, 100.*t_center/t_all, 100.*t_size/t_all, 100.*t_full/t_all)
        
        plotting.line.plotHistory(evt["analysis"]["offCenterX"])
        plotting.line.plotHistory(evt["analysis"]["offCenterY"])
        plotting.line.plotHistory(evt["analysis"]["diameter"])
        plotting.line.plotHistory(evt["analysis"]["intensity"])
        plotting.line.plotHistory(evt["analysis"]["error"])

        plotting.line.plotHistory(evt["parameters"]["offCenterX"])
        plotting.line.plotHistory(evt["parameters"]["offCenterY"])
        plotting.line.plotHistory(evt["parameters"]["diameter"])
        plotting.line.plotHistory(evt["parameters"]["intensity"])

        # Attach a message to the plots
        s0 = evt["analysis"]["diameter"].data
        s1 = evt["parameters"]["diameter"].data
        I0 = evt["analysis"]["intensity"].data
        I1 = evt["parameters"]["intensity"].data
        msg_glo = "diameter = %.2f nm, \nintensity = %.2f mJ/um2" % (s0, I0)
        msg_fit = "Fit result: \ndiameter = %.2f nm (%.2f nm), \nintensity = %.2f mJ/um2 (%.2f mJ/um2)" % (s0, s1-s0, I0, I1-I0)

        # Plot the glorious shots
        plotting.image.plotImage(evt["photonPixelDetectors"]["CCD"], msg=msg_glo, log=True, mask=mask)
        
        # Plot the fitted model
        plotting.image.plotImage(evt["analysis"]["fit"], msg=msg_fit, log=True, mask=mask)
        
