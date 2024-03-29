import os
import time

from hummingbird import analysis, ipc, plotting, simulation, utils
from hummingbird.backend import ureg

sim = simulation.condor.Simulation("examples/advanced/sizing/virus.conf")
sim.hitrate = 1.

state = {
    'Facility': 'Dummy',

    'Dummy': {
        'Repetition Rate' : 10,
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

# Downsamplig
downsampling = 8

# Model parameters for sphere
# ---------------------------
modelParams = {
    'wavelength':0.12398,
    'pixelsize':110*downsampling,
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
    'photon_counting':False}


this_dir = os.path.dirname(os.path.realpath(__file__))
mask = utils.reader.MaskReader(this_dir + "/mask_pnccd.h5","/data/data").boolean_mask
    
def onEvent(evt):

    # Processing rate
    analysis.event.printProcessingRate()

    # Detector statistics
    #analysis.pixel_detector.printStatistics(evt["photonPixelDetectors"])

    # Count Nr. of Photons
    analysis.pixel_detector.totalNrPhotons(evt,evt["photonPixelDetectors"]["CCD"])
    plotting.line.plotHistory(evt["analysis"]["nrPhotons"], label='Nr of photons / frame', history=50)

    # Simple hitfinding (Count Nr. of lit pixels)
    analysis.hitfinding.countLitPixels(evt, evt["photonPixelDetectors"]["CCD"], aduThreshold=0.5, hitscoreThreshold=10)

    # Compute the hitrate
    analysis.hitfinding.hitrate(evt, evt["analysis"]["litpixel: isHit"], history=500)
    
    # Plot the hitscore
    plotting.line.plotHistory(evt["analysis"]["litpixel: hitscore"], label='Nr. of lit pixels', runningHistogram=False)

    # Plot the hitrate
    if ipc.mpi.is_main_slave():
        plotting.line.plotHistory(evt["analysis"]["hitrate"], label='Hit rate [%]')
    
    # Perform sizing on hits
    if evt["analysis"]["litpixel: isHit"]:

        # Downsampling
        t0 = time.time()
        analysis.pixel_detector.bin(evt, "photonPixelDetectors", "CCD", downsampling, mask)
        mask_binned = evt["analysis"]["binned mask - CCD"].data
        t_downsampling = time.time()-t0

        # Find the center of diffraction        
        t0 = time.time()
        analysis.sizing.findCenter(evt, "analysis", "binned image - CCD", mask=mask_binned, maxshift=20, threshold=0.5, blur=4)
        t_center = time.time()-t0
        
        # Fitting sphere model to get size and intensity
        t0 = time.time()
        analysis.sizing.fitSphere(evt, "analysis", "binned image - CCD", mask=mask_binned, **dict(modelParams, **sizingParams))
        t_size = time.time()-t0

        # Fitting model
        t0 = time.time()
        analysis.sizing.sphereModel(evt, "analysis", "offCenterX", "offCenterY", "diameter", "intensity",
                                    (sim._ny//downsampling,sim._nx//downsampling), poisson=True, **modelParams)
        t_full = time.time()-t0

        t_all = t_downsampling + t_center + t_size + t_full
        print("Time: %g sec (downsampling / center / size / full : %.2f%% %.2f%% / %.2f%% / %.2f%%)" % (t_all, 100.*t_downsampling/t_all,
                                                                                                        100.*t_center/t_all,
                                                                                                        100.*t_size/t_all,
                                                                                                        100.*t_full/t_all))
        
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
        msg_fit = "Fit result: \ndiameter = %.2f nm (%.2f nm), \nintensity = %.2f mJ/um2 (%.2f mJ/um2)" % (s0, s1, I0, I1-I0)

        # Plot the glorious shots
        plotting.image.plotImage(evt["analysis"]["binned image - CCD"], msg=msg_glo, log=True, mask=mask_binned)
        
        # Plot the fitted model
        plotting.image.plotImage(evt["analysis"]["fit"], msg=msg_fit, log=True, mask=mask_binned)
        
