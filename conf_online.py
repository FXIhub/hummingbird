# Import analysis/plotting modules
import analysis.event
import analysis.hitfinding
import analysis.pixel_detector
import analysis.sizing
import plotting.image
import plotting.line
import plotting.correlation
import plotting.histogram
from backend.record import add_record
import numpy as np
import time
import ipc
import utils.reader

scanInjector = False
scanXmin = 88
scanXmax = 100
scanXbins = 220/2
scanZmin = 88
scanZmax = 100
scanZbins = 220/2

outputEveryImage = False
do_sizing = True
do_showhybrid = True
move_half = True

#Detector params
detector_distance = 220e-03
gap_top=2.8e-03
gap_bottom=3.1e-03
gap_total=gap_top+gap_bottom
ny=1024
nx=1024
pixel_size=7.5e-05

center_shift=int((gap_top-gap_bottom)/pixel_size)

# Quick config parameters
# hitScoreThreshold = 9000
# aduThreshold = 200
hitScoreThreshold = 25000
aduThreshold = 200
strong_hit_threshold = 60000

# Specify the facility
state = {}
state['Facility'] = 'FLASH'
# Specify folders with frms6 and darkcal data
state['FLASH/DataGlob'] = "/data/beamline/current/raw/pnccd/block-01/holography*0021*.frms6"
state['FLASH/CalibGlob'] = "/data/beamline/current/processed/calib/block-01/*.darkcal.h5"
state['FLASH/DAQFolder'] = "/asap3/flash/gpfs/bl1/2017/data/11001733/processed/daq/"
state['FLASH/MotorFolder'] = '/home/tekeberg/Beamtimes/Holography2017/motor_positions/motor_data.data'
state['do_offline'] = True
#state['FLASH/ProcessingRate'] = 1



#Mask
#Mask out center
Mask = utils.reader.MaskReader("/asap3/flash/gpfs/bl1/2017/data/11001733/processed/mask_v1.h5", "/data")
mask = Mask.boolean_mask
mask_center=np.ones((ny, nx), dtype=np.bool)
radius=30
cx=0
cy=0
xx,yy=np.meshgrid(np.arange(nx), np.arange(ny))
rr=(xx-nx/2)**2+(yy-ny/2)**2 >= (radius**2)
mask_center &= rr
mask_center &= mask

# Sizing
# ------
binning = 4

centerParams = {'x0'       : (512 - (nx-1)/2.)/binning,
                'y0'       : (512 + center_shift -(ny-1)/2.)/binning,
                'maxshift' : int(np.ceil(10./binning)),
                'threshold': 1,
                'blur'     : 4}

modelParams = {'wavelength': 5.2, #in nm
               'pixelsize': 75*binning, #um
               'distance': 220., #mm
               'material': 'sucrose'}

sizingParams = {'d0':20., # in nm
                'i0':1., # in mJ/um2
                'brute_evals':10}

# Physical constants
h = 6.62606957e-34 #[Js]
c = 299792458 #[m/s]
hc = h*c  #[Jm]
eV_to_J = 1.602e-19 #[J/eV]

#res = modelParams["distance"] * 1E-3* modelParams["wavelength"] * 1E-9 / ( pixelsize_native * nx_front )
#expected_diameter = 150

# Thresholds for good sizing fits
fit_error_threshold = 2.6E-3#4.0e-3
photon_error_threshold = 3000
diameter_min = 40  #[nm]
diameter_max = 90 #[nm]

def calculate_epoch_times(evt, time_sec, time_usec):
    add_record(evt['ID'], 'ID', 'time', time_sec.data + 1.e-6*time_usec.data)
    #add_record(evt['ID'], 'ID', 'timeAgo', time.time() - (time_sec.data + 1.e-6*time_usec.data))
    # Calculating timeAgo with 606 second offset due to miscalibration of pnCCD server clock
    #add_record(evt['ID'], 'ID', 'timeAgo', -606. + time.time() - (time_sec.data + 1.e-6*time_usec.data))
    add_record(evt['ID'], 'ID', 'timeAgo', 0. + time.time() - (time_sec.data + 1.e-6*time_usec.data))

# This function is called for every single event
# following the given recipe of analysis
def onEvent(evt):
    # Processing rate [Hz]
    #analysis.event.printProcessingRate()

    # Calculate time and add to PlotHistory
    # calculate_epoch_times(evt, evt["ID"]["tv_sec"], evt["ID"]["tv_usec"])
    # plotting.line.plotHistory(evt['ID']['timeAgo'], label='Event Time (s)', group='ID')
    # plotting.line.plotHistory(evt['ID']['tv_sec'], label='Epoch Time (s)', group='ID')
    detector_type = "photonPixelDetectors"
    detector_key  = "pnCCD"
    if move_half:
        detector = evt[detector_type][detector_key]
        detector = analysis.pixel_detector.moveHalf(evt, detector, horizontal=gap_total/pixel_size, outkey='data_half-moved')
        mask_center_s = analysis.pixel_detector.moveHalf(evt, add_record(evt["analysis"], "analysis", "mask", mask_center), horizontal=gap_total/pixel_size, outkey='mask_half-moved').data
        detector_type = "analysis"
        detector_key  = "data_half-moved"
    # Do basic hitfinding using lit pixels
    analysis.hitfinding.countLitPixels(evt, evt[detector_type][detector_key], 
                                       aduThreshold=aduThreshold, 
                                       hitscoreThreshold=hitScoreThreshold, mask=mask_center_s)

    hit = bool(evt["analysis"]["litpixel: isHit"].data)
    strong_hit=evt["analysis"]["litpixel: hitscore"].data>strong_hit_threshold
    plotting.line.plotHistory(evt["analysis"]["litpixel: hitscore"],
                              label='Nr. of lit pixels', hline=hitScoreThreshold, group='Metric')
    analysis.hitfinding.hitrate(evt, hit, history=50)

    if scanInjector:
        plotting.histogram.plotNormalizedHistogram(evt["motorPositions"]["InjectorX"], float(1 if hit else 0), hmin=scanXmin, hmax=scanXmax, bins=scanXbins, name="Histogram: InjectorX x Hitrate", group="Scan", buffer_length=1000)
        plotting.histogram.plotNormalizedHistogram(evt["motorPositions"]["InjectorZ"], float(1 if hit else 0), hmin=scanZmin, hmax=scanZmax, bins=scanZbins, name="Histogram: InjectorZ x Hitrate", group="Scan", buffer_length=1000)

        plotting.correlation.plotScatter(evt["motorPositions"]["InjectorX"], evt['analysis']['litpixel: hitscore'], 
                                         name='InjectorX vs Hitscore', xlabel='InjectorX', ylabel='Hit Score',
                                         group='Scan')
        plotting.correlation.plotScatter(evt["motorPositions"]["InjectorZ"], evt['analysis']['litpixel: hitscore'], 
                                         name='InjectorZ vs Hitscore', xlabel='InjectorZ', ylabel='Hit Score',
                                         group='Scan')
        plotting.line.plotHistory(evt["motorPositions"]["InjectorX"], label="Cluster delay", group="Scan")
        plotting.line.plotHistory(evt["motorPositions"]["InjectorZ"], label="Nothing", group="Scan")
        # print("InjectorX = {0}".format(evt["motorPositions"]["InjectorX"].data))


    if outputEveryImage:
        plotting.image.plotImage(evt[detector_type][detector_key], name="pnCCD (All)", group='Images')

    if ipc.mpi.is_main_worker():
        plotting.line.plotHistory(evt["analysis"]["hitrate"], label='Hit rate [%]', group='Metric', history=10000)
        # plotting.correlation.plotMeanMap(evt['motorPositions']['nozzle_x'], evt['motorPositions']['nozzle_y'],
        #                              #evt['analysis']['litpixel: hitscore'].data / 1e5, 
        #                              evt['analysis']['hitrate'].data, 
        #                              xmin=0.68, xmax=0.72, ymin=4.20, ymax=4.23,
        #                              name='Hitscore mean map vs nozzle_xy',
        #                              xlabel='nozzle_x (mm)', 
        #                              ylabel='nozzle_y (mm)',
        #                              group='Metric')
    if hit:
        plotting.image.plotImage(evt[detector_type][detector_key], name="pnCCD (Hits)", group='Images', mask=mask_center_s)
        if do_sizing:
            # Crop to 1024 x 1024
            Nx,Ny=np.shape(evt[detector_type][detector_key].data)
            diff_y=Ny-1024
            cropped_img=evt[detector_type][detector_key].data[:,diff_y/2:-(diff_y/2)]
            add_record(evt["analysis"], "analysis", "data-cropped", cropped_img)
            detector_key = "data-cropped"
            cropped_mask=mask_center_s[:,diff_y/2:-(diff_y/2)]
            add_record(evt["analysis"], "analysis", "mask-cropped", cropped_mask)
            mask_center_fit_s = evt['analysis']['mask-cropped'].data
            
            # Binning
            analysis.pixel_detector.bin(evt, detector_type, detector_key, binning, mask_center_fit_s)
            mask_binned = evt["analysis"]["binned mask - " + detector_key].data
            detector_type_b = "analysis"
            detector_key_b = "binned image - " + detector_key
            
            # CENTER DETERMINATION
            analysis.sizing.findCenter(evt, detector_type_b, detector_key_b, mask=mask_binned, **centerParams)
            # RADIAL AVERAGE
            analysis.pixel_detector.radial(evt, detector_type_b, detector_key_b, mask=mask_binned, cx=evt["analysis"]["cx"].data, cy=evt["analysis"]["cy"].data)          
            # FIT SPHERE MODEL
            analysis.sizing.fitSphereRadial(evt, "analysis", "radial distance - " + detector_key_b, "radial average - " + detector_key_b, **dict(modelParams, **sizingParams))
            # DIFFRACTION PATTERN FROM FIT
            analysis.sizing.sphereModel(evt, "analysis", "offCenterX", "offCenterY", "diameter", "intensity", (ny/binning,nx/binning), poisson=False, **modelParams)
            # RADIAL AVERAGE FIT
            analysis.pixel_detector.radial(evt, "analysis", "fit", mask=mask_binned, cx=evt["analysis"]["cx"].data, cy=evt["analysis"]["cy"].data)
            # ERRORS
            #analysis.sizing.photon_error(evt, detector_type_b, detector_key_b, "analysis", "fit", adu_per_photon=144.)
            #analysis.sizing.absolute_error(evt, detector_type_b, detector_key_b, "analysis", "fit", "absolute error")
            msg = "diameter: %.2f nm \nIntensity: %.4f mJ/um2\nFit Error: %.2e" %(evt["analysis"]["diameter"].data, evt["analysis"]["intensity"].data, evt["analysis"]["fit error"].data)
            # Selection of good fits
            small_fit_error    = evt['analysis']['fit error'].data    < fit_error_threshold
            #small_photon_error = evt['analysis']['photon error'].data < photon_error_threshold
            correctsized_hit = small_fit_error #and small_photon_error

            # Select only events in a certain diameter window
            diameter = evt['analysis']['diameter'].data
            #print diameter
            plotting.histogram.plotHistogram(evt["analysis"]["diameter"], bins=100, name="Histogram: Particle size", group="Sizing", hmin=20, hmax=100, buffer_length=1000)
            correctsized_hit &= ((diameter > diameter_min) & (diameter < diameter_max))
            
            # Plot errors
            plotting.line.plotHistory(evt["analysis"]["fit error"], history=1000, hline=fit_error_threshold, group='Sizing')
            #plotting.line.plotHistory(evt["analysis"]["photon error"], history=1000, hline=photon_error_threshold, group='Sizing')
            #plotting.line.plotHistory(evt["analysis"]["absolute error"], history=1000, group='Sizing')
            #time.sleep(0.05)
            if do_showhybrid:
                # HYBRID PATTERN
                hybrid = evt["analysis"]["fit"].data.copy()
                hybrid[:,512/binning:] = evt[detector_type_b][detector_key_b].data[:,512/binning:]
                add_record(evt["analysis"], "analysis", "Hybrid pattern", hybrid)
                
                plotting.image.plotImage(evt["analysis"]["Hybrid pattern"], 
                                         name="Hybrid pattern ", msg=msg, group='Sizing')
                
                plotting.image.plotImage(evt["analysis"]["Hybrid pattern"], 
                                         name="Hybrid pattern / log", 
                                         vmax=1e4, log=True, 
                                         msg=msg, group='Sizing')
                        

            if correctsized_hit and strong_hit:
                # Plot Correct sized hits
                print 'strong hit!'
                plotting.image.plotImage(evt[detector_type][detector_key], group='Sizing', msg=msg, name="pnCCD front (correct hit)", mask=mask_center_fit_s)
                
                # Plot Intensity
                plotting.line.plotHistory(evt["analysis"]["intensity"], history=10000, name ='Intensity (from sizing)', group='Results')
                # Plot size (in nm)
                plotting.line.plotHistory(evt["analysis"]["diameter"], history=10000, name = 'Size in nm (from sizing)', group='Results')
                # Normalizing intensity to pulse energy (assuming 1mJ on average)
                #intensity_normalized = (evt['analysis']['intensity'].data / evt['analysis']['averagePulseEnergy'].data) * 1.0
                #add_record(evt['analysis'], 'analysis', 'intensity_normalized', intensity_normalized)
                
                # Plot Intensity (normalized)
                plotting.line.plotHistory(evt['analysis']['intensity'], history=10000, name = 'Intensity normalized (from sizing)', group='Results')
                
                # Center position
                #plotting.correlation.plotMeanMap(evt["analysis"]["cx"], evt["analysis"]["cy"], intensity_normalized, group='Results',name='Wavefront (center vs. intensity)', xmin=-10, xmax=10, xbins=21, ymin=-10, ymax=10, ybins=21, xlabel='Center position in x', ylabel='Center position in y')

