import os,sys
import numpy
import analysis.event
import analysis.beamline
import analysis.hitfinding
import analysis.pixel_detector
import analysis.stack
import analysis.recorder
import analysis.sizing
import analysis.injection_camera
import plotting.image
import plotting.line
import plotting.correlation
import backend
import ipc  
import utils.reader
import utils.array
this_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(this_dir)
import diagnostics


# Flags
# -----

# Lots of ouput
do_diagnostics    = False
# Sizing
do_sizing         = True
# Running from shared memory
do_online         = False
# Make sure to run online on cxiopr
do_autoonline     = True
# Front detector activated
do_front          = True
# Do assembly of the front
do_assemble_front = True
# Send the 2x2 images all events to the frontend
do_showall        = True
# Common mode correction for hits
do_cmc            = True
# Running background subtraction for hits
do_bgsub          = False
# Particle camera
do_camera         = False

# ---------------------------------------------------------
# P S A N A
# ---------------------------------------------------------
state = {}
state['Facility'] = 'LCLS'

cxiopr = False
if do_autoonline:
    import getpass
    if getpass.getuser() == "cxiopr":
        do_online  = True
        cxiopr     = True

if do_online:
    state['LCLS/DataSource'] = 'shmem=psana.0:stop=no'
else:
    state['LCLS/DataSource'] = 'exp=cxi86715:run=70'

if do_front:
    state['LCLS/PsanaConf'] = 'psana_cfg/both_cspads.cfg'
else:
    state['LCLS/PsanaConf'] = 'psana_cfg/cspad2x2.cfg'

# CSPAD 2x2
# ---------
c2x2_type = "image"
c2x2_key  = "CsPad Dg2[image]"

# CSPAD large
# -----------
clarge_type = "photons"
#clarge_type = "calibrated"
clarge_key  = "CsPad Ds2[%s]" % clarge_type

# INJECTOR MOTORS
# ---------------
injector_x_key = "CXI:PI2:MMS:01.RBV"
injector_y_key = "CXI:PI2:MMS:02.RBV"
injector_z_key = "CXI:PI2:MMS:03.RBV"

# ---------------------------------------------------------
# P A R A M E T E R S
# ---------------------------------------------------------

# Mask
# ----
M_back    = utils.reader.MaskReader(this_dir + "/mask/mask_back.h5","/data/data")
mask_c2x2 = M_back.boolean_mask
(ny_c2x2,nx_c2x2) = mask_c2x2.shape
M_beamstops = utils.reader.MaskReader(this_dir + "/mask/beamstops_back.h5","/data/data")
beamstops_c2x2 = M_beamstops.boolean_mask

# Geometry
# --------
pixel_size = 110E-6
G_front = utils.reader.GeometryReader(this_dir + "/geometry/geometry_front.h5", pixel_size=110.E-6)
x_front = numpy.array(utils.array.cheetahToSlacH5(G_front.x), dtype="int")
y_front = numpy.array(utils.array.cheetahToSlacH5(G_front.y), dtype="int")

# Hit finding
# -----------
aduThreshold = 25
if do_online:
    #hitscoreThreshold = 20
    #hitscoreThreshold = 4500
    hitscoreThreshold = 400
    hitscoreDark = 20
else:
    hitscoreThreshold =  0
    hitscoreDark = 0

# Sizing
# ------
centerParams = {
    'x0'       : 242 - (nx_c2x2-1)/2.,
    'y0'       : 212 - (ny_c2x2-1)/2.,
    'maxshift' : 50,
    'threshold': 0.5,
    'blur'     : 4,
}
modelParams = {
    'wavelength':0.1795,
    'pixelsize':110,
    'distance':2400,
    'material':'virus',
}
sizingParams = {
    'd0':100,
    'i0':1,
    'brute_evals':10,
}

# Classification
# --------------
fit_error_threshold  = 0.5
diameter_expected    = 70
diameter_error_max   = 30

# Background
# ----------
bgall = False
Nbg   = 100
rbg   = 5000
obg   = 5000
bg = analysis.stack.Stack(name="bg",maxLen=Nbg,outPeriod=obg,reducePeriod=rbg)
if cxiopr:
    bg_dir = "/reg/neh/home/hantke/cxi86715_scratch/stack/"
else:
    bg_dir = this_dir + "/stack"

# Recording
# ---------
recordlist = {
    'size': ('analysis', 'diameter'),
    'intensity': ('analysis', 'intensity'),
    'error': ('analysis', 'fit error'),
    'hitscore': ('analysis', 'hitscore - ' + c2x2_key)
}
if do_online:
    recorddir = '/reg/neh/home/hantke/cxi86715_scratch/online/hits/'
else:
    recorddir = '/reg/d/psdm/cxi/cxi86715/scratch/hummingbird/offline_hits/'
recorder = analysis.recorder.Recorder(recorddir, recordlist, ipc.mpi.rank, maxEvents=10000)
    
# Plotting
# --------
# Radial averages
radial_tracelen = 100

# Injector position limits
x_min = -3
x_max = -1
x_bins = 50
y_min = -40
y_max = -35
y_bins = 100
z_min = -7
z_max = -5
z_bins = 50

# Hitrate mean map 
hitrateMeanMapParams = {
    'xmin': x_min,
    'xmax': x_max,
    'ymin': z_min,
    'ymax': z_max,
    'xbins': x_bins,
    'ybins': z_bins,
    'xlabel': 'Injector Position in x',
    'ylabel': 'Injector Position in z'  
}

# Hitscore mean map 
hitscoreMeanMapParams = {
    'xmin': x_min,
    'xmax': x_max,
    'ymin': z_min,
    'ymax': z_max,
    'xbins': x_bins,
    'ybins': z_bins,
    'xlabel': 'Injector Position in x',
    'ylabel': 'Injector Position in z'  
}

# Diameter mean map
diameterMeanMapParams = {
    'xmin': x_min,
    'xmax': x_max,
    'ymin': z_min,
    'ymax': z_max,
    'xbins': 10,
    'ybins': 10,
    'xlabel': 'Injector Position in y',
    'ylabel': 'Injector Position in z'  
}

# Mean map of hitrate as function of diameter and intensity
sizingMeanMapParams = {
    'xmin': 40,
    'xmax': 240,
    'ymin': 0,
    'ymax': 1,
    'xbins': 20,
    'ybins': 100,
    'xlabel': 'Diameter in [nm]',
    'ylabel': 'Intensity in [mJ/um2]'  
}

# Diameter mean map
intensityMeanMapParams = {
    'xmin': x_min,
    'xmax': x_max,
    'ymin': z_min,
    'ymax': z_max,
    'xbins': 10,
    'ybins': 10,
    'xlabel': 'Injector Position in x',
    'ylabel': 'Injector Position in z'  
}

# Image
vmin_c2x2 = 0
vmax_c2x2 = 100
vmin_clarge = 0
vmax_clarge = 10

# ---------------------------------------------------------
# E V E N T   C A L L
# ---------------------------------------------------------

def onEvent(evt):

    # ------------------- #
    # INITIAL DIAGNOSTICS #
    # ------------------- #

    # Time measurement
    analysis.event.printProcessingRate()
    #analysis.event.printID(evt["eventID"])
    #print evt.native_keys()

    # Send Fiducials and Timestamp
    plotting.line.plotTimestamp(evt["eventID"]["Timestamp"])
    
    # Spit out a lot for debugging
    if do_diagnostics: diagnostics.initial_diagnostics(evt)
    
    # -------- #
    # ANALYSIS #
    # -------- #
    #print evt.native_keys()

    # AVERAGE PULSE ENERGY
    analysis.beamline.averagePulseEnergy(evt, "pulseEnergies")

    # HIT FINDING
    #analysis.hitfinding.countTof(evt, "ionTOFs", "Acqiris 0 Channel 0")

    # Simple hit finding by counting lit pixels
    analysis.hitfinding.countLitPixels(evt, c2x2_type, c2x2_key, aduThreshold=aduThreshold, hitscoreThreshold=hitscoreThreshold, hitscoreDark=hitscoreDark, mask=mask_c2x2)
    hit  = evt["analysis"]["isHit - " + c2x2_key].data
    miss = evt["analysis"]["isMiss - " + c2x2_key].data

    # CAMERA
    doing_camera = False
    if do_camera and "Sc2Questar[camimage]" in evt["camimage"]:        
        analysis.injection_camera.getMaskedParticles(evt, "camimage", "Sc2Questar[camimage]", "maskedcamera", minX = 200, maxX = 1300, thresh = 30)
        analysis.injection_camera.countContours(evt, "image", "Sc2Questar[camimage]", "maskedcamera", "coloredmask", "particlestream")
        doing_camera = True

    # COUNT PHOTONS
    # Count photons in different detector regions
    analysis.pixel_detector.totalNrPhotons(evt, c2x2_type, c2x2_key, aduPhoton=20, aduThreshold=10)
    if do_front:
        analysis.pixel_detector.getCentral4Asics(evt, clarge_type, clarge_key)
        if do_assemble_front:
            analysis.pixel_detector.assemble(evt, clarge_type, clarge_key, x=x_front, y=y_front, nx=400, ny=400, subset=map(lambda i : (i * 8 + 1) * 2, xrange(4)))
        analysis.pixel_detector.totalNrPhotons(evt, clarge_type, clarge_key, aduPhoton=1, aduThreshold=0.5)
        analysis.pixel_detector.totalNrPhotons(evt, "analysis", "central4Asics", aduPhoton=1, aduThreshold=0.5)

        
    if miss or bgall:
        #print "MISS (hit score %i < %i)" % (evt["analysis"]["hitscore - " + c2x2_key].data, hitscoreThreshold)
        # COLLECTING BACKGROUND
        # Update
        bg.add(evt[c2x2_type][c2x2_key].data)
        # Reduce
        bg.reduce()
        # Write to file
        bg.write(evt,directory=bg_dir)
        
    if hit:
        print "HIT (hit score %i > %i)" % (evt["analysis"]["hitscore - " + c2x2_key].data, hitscoreThreshold)
        good_hit = False
        if do_sizing:
            if do_cmc:
                # CMC
                analysis.pixel_detector.cmc(evt, c2x2_type, c2x2_key, mask=beamstops_c2x2)
                c2x2_type_s = "analysis"
                c2x2_key_s = "cmc - " + c2x2_key            
            if do_bgsub:
                # Running background subtraction
                analysis.pixel_detector.bgsub(evt, c2x2_type_s, c2x2_key_s, bg=bg.last_mean)
                c2x2_type_s = "analysis"
                c2x2_key_s = "bgsub - " + c2x2_key_s            
            if not do_cmc and not do_bgsub:
                c2x2_type_s = c2x2_type
                c2x2_key_s = c2x2_key
            # RADIAL SPHERE FIT
            # Find the center of diffraction
            analysis.sizing.findCenter(evt, c2x2_type_s, c2x2_key_s, mask=mask_c2x2, **centerParams)
            # Calculate radial average
            analysis.pixel_detector.radial(evt, c2x2_type_s, c2x2_key_s, mask=mask_c2x2, cx=evt["analysis"]["cx"].data, cy=evt["analysis"]["cy"].data)          
            # Fitting sphere model to get size and intensity
            analysis.sizing.fitSphereRadial(evt, "analysis", "radial distance - " + c2x2_key_s, "radial average - " + c2x2_key_s, **dict(modelParams, **sizingParams))
            # Calculate diffraction pattern from fit result 
            analysis.sizing.sphereModel(evt, "analysis", "offCenterX", "offCenterY", "diameter", "intensity", (ny_c2x2,nx_c2x2), poisson=False, **modelParams)
            # Calculate radial average of diffraction pattern from fit result
            analysis.pixel_detector.radial(evt, "analysis", "fit", mask=mask_c2x2, cx=evt["analysis"]["cx"].data, cy=evt["analysis"]["cy"].data)
            # Decide whether or not the fit was successful
            fit_succeeded = evt["analysis"]["fit error"].data < fit_error_threshold
            if fit_succeeded:
                # Decide whether or not this was a good hit, i.e. a hit in the expected size range
                good_hit = abs(evt["analysis"]["diameter"].data - diameter_expected) <= diameter_error_max
            backend.add_record(evt["analysis"], "analysis", "Good hit rate", float(good_hit))

        # Record hits together with sizing results
		recorder.setup_file_if_needed(evt)
        recorder.append(evt)
                
    # ------------------------ #
    # Send RESULT TO INTERFACE #
    # ------------------------ #

    # Send stuf from particle stream
    if doing_camera:
        plotting.line.plotHistogram(evt["analysis"]["particlestream"], log10=True, hmin=1, hmax=8, bins=1000)
        plotting.image.plotImage(evt["camimage"]["Sc2Questar[camimage]"], msg="")
        plotting.image.plotImage(evt["analysis"]["maskedcamera"], msg="", name="Masked Opal image")                                                                

    # If not miss or hit, probably dark run -> do not send anything
    #if not (miss or hit):
    #    return 
    
    # Pulse Energy
    plotting.line.plotHistory(evt["analysis"]["averagePulseEnergy"])

    # Injector position (z is along the beam, x is across the beam)
    x = evt["parameters"][injector_x_key]
    #y = evt["parameters"][injector_y_key]
    z = evt["parameters"][injector_z_key]
    plotting.line.plotHistory(x)
    #plotting.line.plotHistory(y)
    plotting.line.plotHistory(z)

    # Injector pressures
    p1 = evt["parameters"]["CXI:SDS:REG:01:PRESS"]
    p2 = evt["parameters"]["CXI:SDS:REG:02:PRESS"]
    
    # HITFINDING
    # Keep hit history for hitrate plots
    plotting.line.plotHistory(evt["analysis"]["isHit - " + c2x2_key])
    # Plot MeanMap of hitrate(y,z)
    #plotting.correlation.plotMeanMap(x, z, evt["analysis"]["hitscore - " + ]], plotid='hitrateMeanMap', **hitrateMeanMapParams)
    # Keep hitscore history
    plotting.line.plotHistory(evt["analysis"]["hitscore - " + c2x2_key], runningHistogram=True, hmin=hitscoreThreshold-100, hmax=hitscoreThreshold+100, bins=100, window=100, history=1000)

    # PHOTON COUNTING
    # Keep history of number of photons on the back
    plotting.line.plotHistory(evt["analysis"]["nrPhotons - " + c2x2_key], runningHistogram=True, hmin=hitscoreThreshold-100, hmax=hitscoreThreshold+100, bins=100, window=100, history=1000)

    # Nr. of photons 
    plotting.line.plotHistory(evt["analysis"]["nrPhotons - " + c2x2_key])
    plotting.line.plotHistory(evt["analysis"]["nrPhotons - " + c2x2_key], runningHistogram=True, hmin=0, hmax=100000, bins=100, window=100, history=1000)
    if do_front:
        plotting.line.plotHistory(evt["analysis"]["nrPhotons - central4Asics"])

    # Plot ScatterPlot with colored hitscore
    #plotting.correlation.plotScatterColor(x,z, evt["analysis"]["hitscore - " + c2x2_key], plotid='hitscoreScatter', vmin=0, vmax=2000, xlabel='Injector X', ylabel='Injectory Z', zlabel='Hitscore')

    if do_showall:        
        # Image of back detector for all events
        plotting.image.plotImage(evt[c2x2_type][c2x2_key], msg="", name="Cspad 2x2: All", mask=mask_c2x2, vmin=vmin_c2x2, vmax=vmax_c2x2)
        # Histogram of detector for all events
        plotting.line.plotHistogram(evt[c2x2_type][c2x2_key], mask=mask_c2x2, hmin=-100, hmax=100, bins=200, label='Cspad 2x2 pixel value [ADU]')
   
    # THIS HERE CAUSED A CRASH
    #plotting.correlation.plotMeanMap(evt["analysis"]["averagePulseEnergy"], evt["analysis"]["nrPhotons - central4Asics"], hit)
    #plotting.line.plotHistory(evt["analysis"]["averagePulseEnergy"])
    
    if hit:

        # Scatter plot of hitscore vs. injector in Z
        plotting.correlation.plotScatter(x, evt["analysis"]["hitscore - " + c2x2_key], plotid='tuneInjectionX', history=10000, xlabel='Injector in X', ylabel='Hitscore')  
        plotting.correlation.plotScatter(z, evt["analysis"]["hitscore - " + c2x2_key], plotid='tuneInjectionZ', history=10000, xlabel='Injector in Z', ylabel='Hitscore')  
        
        # Scatter plot for hitscore vs. injector pressure
        plotting.correlation.plotScatter(p1, evt["analysis"]["hitscore - " + c2x2_key], plotid='tuneInjectionP1', history=10000, xlabel='Injector in X', ylabel='Hitscore')  
        plotting.correlation.plotScatter(p2, evt["analysis"]["hitscore - " + c2x2_key], plotid='tuneInjectionP2', history=10000, xlabel='Injector in Z', ylabel='Hitscore')  
        
        # ToF
        plotting.line.plotTrace(evt["ionTOFs"]["Acqiris 0 Channel 1"]) 
        
        # Image of hit
        plotting.image.plotImage(evt[c2x2_type][c2x2_key], msg='', name="Cspad 2x2: Hit", vmin=vmin_c2x2, vmax=vmax_c2x2 )      

        if do_sizing:
            if do_cmc or do_bgsub:
                # Image of hit (cmc corrected)
                plotting.image.plotImage(evt[c2x2_type_s][c2x2_key_s], msg="", mask=mask_c2x2, name="Cspad 2x2: Hit (corrected)", vmin=vmin_c2x2, vmax=vmax_c2x2)
        
        if do_front:
            # Front detector image (central 4 asics) of hit
            #plotting.image.plotImage(evt[clarge_type][clarge_key])
            plotting.image.plotImage(evt["analysis"]["central4Asics"], vmin=vmin_clarge, vmax=vmax_clarge)
            if do_assemble_front:
                plotting.image.plotImage(evt["analysis"]["assembled - " + clarge_key], msg="", name="Cspad large (central 4 asics): Hit", vmin=vmin_clarge, vmax=vmin_clarge)

        if do_sizing:

            # Image of fit
            msg = "diameter: %.2f nm \nIntensity: %.2f mJ/um2" %(evt["analysis"]["diameter"].data, evt["analysis"]["intensity"].data)
            plotting.image.plotImage(evt["analysis"]["fit"], log=True, mask=mask_c2x2, name="Cspad 2x2: Fit result (radial sphere fit)", vmin=vmin_c2x2, vmax=vmax_c2x2, msg=msg)
            
            # Plot measurement radial average
            plotting.line.plotTrace(evt["analysis"]["radial average - "+c2x2_key_s], evt["analysis"]["radial distance - "+c2x2_key_s],tracelen=radial_tracelen)
            # Plot fit radial average
            plotting.line.plotTrace(evt["analysis"]["radial average - fit"], evt["analysis"]["radial distance - fit"], tracelen=radial_tracelen)         
            # Fit error history
            plotting.line.plotHistory(evt["analysis"]["fit error"])

            if fit_succeeded:

                # Plot parameter histories
                plotting.line.plotHistory(evt["analysis"]["offCenterX"])
                plotting.line.plotHistory(evt["analysis"]["offCenterY"])
                plotting.line.plotHistory(evt["analysis"]["diameter"], runningHistogram=True)
                plotting.line.plotHistory(evt["analysis"]["intensity"], runningHistogram=True)
                plotting.correlation.plotMeanMap(x,z,evt["analysis"]["diameter"].data, plotid='DiameterMeanMap', **diameterMeanMapParams)
                plotting.correlation.plotMeanMap(x,z,evt["analysis"]["intensity"].data, plotid='IntensityMeanMap', **intensityMeanMapParams)

                # Diameter vs. intensity scatter plot
                plotting.correlation.plotScatter(evt["analysis"]["diameter"], evt["analysis"]["intensity"], plotid='Diameter vs. intensity', history=100)

                if good_hit:

                    # Image of good hit
                    plotting.image.plotImage(evt[c2x2_type][c2x2_key], msg="", log=True, mask=mask_c2x2, name="Cspad 2x2: Hit and correct particle size", vmin=vmin_c2x2, vmax=vmax_c2x2)
                    
                    if do_front:
                        # Front detector image of good hit
                        plotting.image.plotImage(evt[clarge_type][clarge_key], msg="", name="Cspad large (full): Correct particle size", vmin=vmin_clarge, vmax=vmax_clarge)       
        
    # ----------------- #
    # FINAL DIAGNOSTICS #
    # ----------------- #
    
    # Spit out a lot for debugging
    if do_diagnostics: diagnostics.final_diagnostics(evt)

