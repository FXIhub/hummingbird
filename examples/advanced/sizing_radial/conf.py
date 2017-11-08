import os
import time
import numpy
import ipc.mpi
import utils.reader
import simulation.condor
import analysis.event
import analysis.pixel_detector
import analysis.hitfinding
import analysis.sizing
import plotting.line
import plotting.image
import plotting.correlation
this_dir = os.path.dirname(os.path.realpath(__file__))


# Configure simulation
# --------------------
sim = simulation.condor.Simulation(this_dir + "/virus.conf")
sim.hitrate = 1.0

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
downsampling = 16

# Model parameters for sphere
# ---------------------------
modelParams = {
    'wavelength':0.12398,
    'pixelsize':110 * downsampling,
    'distance':2160,
    'adu_per_photon':1,
    'quantum_efficiency':1.,
    'material':'virus'}

# Sizing parameters
# -----------------
radial = True
sizingParams = {
    'd0':100,
    'i0':1,
    'mask_radius':100,
    'brute_evals':10,
    'photon_counting':True}

# Detector
# --------
nx = sim._nx
ny = sim._ny

# Loading of mask
# ---------------
mask = utils.reader.MaskReader(this_dir + "/mask_pnccd.h5","/data/data").boolean_mask

# Error logging histories
# -----------------------
histLen = 100
I = numpy.zeros(histLen)*numpy.nan
Ierr = numpy.zeros(histLen)*numpy.nan
s = numpy.zeros(histLen)*numpy.nan
serr = numpy.zeros(histLen)*numpy.nan
ferr = numpy.zeros(histLen)*numpy.nan
fl = numpy.zeros(histLen)*numpy.nan
sph = numpy.zeros(histLen)*numpy.nan
i = 0

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
    plotting.line.plotHistory(evt["analysis"]["litpixel: hitscore"], label='Nr. of lit pixels')

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

        t0 = time.time()
        # Find the center of diffraction
        analysis.sizing.findCenter(evt, "analysis", "binned image - CCD", mask=mask_binned, maxshift=20, threshold=0.5, blur=4)
        t_center = time.time()-t0

        if not radial:
            # Fitting sphere model to get size and intensity
            t0 = time.time()
            analysis.sizing.fitSphere(evt, "analysis", "binned image - CCD", mask=mask_binned, downsampling=1, **dict(modelParams, **sizingParams))
            t_size = time.time()-t0
            
        else:
            # Calculate radial average
            t0 = time.time()
            cx = evt["analysis"]["offCenterX"].data + (nx//downsampling - 1) / 2.  
            cy = evt["analysis"]["offCenterY"].data + (ny//downsampling - 1) / 2.
            analysis.pixel_detector.radial(evt, "analysis", "binned image - CCD", mask=mask_binned, cx=cx, cy=cy)
            # Fitting sphere model to get size and intensity
            analysis.sizing.fitSphereRadial(evt, "analysis", "radial distance - binned image - CCD", "radial average - binned image - CCD", **dict(modelParams, **sizingParams))
            t_size = time.time()-t0

        # Fitting model
        t0 = time.time()
        analysis.sizing.sphereModel(evt, "analysis", "offCenterX", "offCenterY", "diameter", "intensity", (ny//downsampling,nx//downsampling), poisson=False, **modelParams)
        t_full = time.time()-t0

        if radial:
            analysis.pixel_detector.radial(evt, "analysis", "fit", mask=mask_binned, cx=cx, cy=cy)
            plotting.line.plotTrace(evt["analysis"]["radial average - fit"], evt["analysis"]["radial distance - fit"], tracelen=100)
            plotting.line.plotTrace(evt["analysis"]["radial average - binned image - CCD"], evt["analysis"]["radial distance - binned image - CCD"], tracelen=100)

        t_all = t_center + t_size + t_full
        print "Time: %g sec (downsampling / center / size / full : %.2f%% %.2f%% / %.2f%% / %.2f%%)" % (t_all, 100.*t_downsampling/t_all, 100.*t_center/t_all, 100.*t_size/t_all, 100.*t_full/t_all)           
        
        plotting.line.plotHistory(evt["analysis"]["offCenterX"])
        plotting.line.plotHistory(evt["analysis"]["offCenterY"])
        plotting.line.plotHistory(evt["analysis"]["diameter"], runningHistogram=True)
        plotting.line.plotHistory(evt["analysis"]["intensity"])
        plotting.line.plotHistory(evt["analysis"]["fit error"])

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

        # Errors
        size_error = analysis.sizing.absolute_error(evt, "analysis", "diameter", "parameters", "diameter", out_key='size error')
        intensity_error = analysis.sizing.absolute_error(evt, "analysis", "intensity", "parameters", "intensity", out_key='intensity error')
                            
        global s
        global I
        global fl
        global sph
        global serr
        global Ierr
        global flerr
        global ferr
        global i
        I[i%histLen] = I1
        s[i%histLen] = s1
        #fl[i%histLen] = evt["parameters"]["flattening"].data
        serr[i%histLen] = evt["analysis"]["size error"].data
        Ierr[i%histLen] = evt["analysis"]["intensity error"].data
        ferr[i%histLen] = evt["analysis"]["fit error"].data
        i += 1
        fin = numpy.isfinite(serr)
        #print "Average errors: ds = %e nm (%.1f %%); dI = %e mJ/um2 (%.1f %%)" % (serr[fin].mean(),
        #                                                                          100.*serr[fin].mean()/s[fin].mean(),
        #                                                                          Ierr[fin].mean(),
        #                                                                          100.*Ierr[fin].mean()/I[fin].mean())
        #print "Median errors: ds = %e nm (%.1f %%); dI = %e mJ/um2 (%.1f %%)" % (numpy.median(serr[fin]),
        #                                                                         100.*numpy.median(serr[fin])/numpy.median(s[fin]),
        #                                                                         numpy.median(Ierr[fin]),
        #                                                                         100.*numpy.median(Ierr[fin])/numpy.median(I[fin]))

        plotting.correlation.plotScatter(evt["analysis"]["size error"], evt["analysis"]["fit error"], name='Size error vs. fit error', history=100)
        plotting.correlation.plotScatter(evt["analysis"]["intensity error"], evt["analysis"]["fit error"], name='Intensity error vs. fit error', history=100)
        
        # Plot the glorious shots
        plotting.image.plotImage(evt["analysis"]["binned image - CCD"], msg=msg_glo, alert=True, log=True, mask=mask_binned)
        
        # Plot the fitted model
        plotting.image.plotImage(evt["analysis"]["fit"], msg=msg_fit, log=True, mask=mask_binned)
        
