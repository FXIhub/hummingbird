# Import analysis/plotting modules
import analysis.event
import analysis.hitfinding
import analysis.pixel_detector
import analysis.sizing
import analysis.patterson
import plotting.image
import plotting.line
import plotting.correlation
import plotting.histogram
from backend.record import add_record
import numpy as np
import scipy.misc as misc
import time
import ipc
import os, sys
import analysis.refocus_hologram
this_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(this_dir)
#import conf
#reload(conf)
from conf import *

# Injector scans
scanInjector = True
scanXmin = -10
scanXmax = 10
scanXbins = 21
scanZmin = 12
scanZmax = 14
scanZbins = 50
scanYmin = 94
scanYmax = 97
scanYbins = 20

outputEveryImage = False
do_sizing = False
do_showhybrid = False
do_patterson = True
do_hologram = True
move_half = True

# Quick config parameters
hitScoreThreshold = 1000
aduThreshold = 200
strong_hit_threshold = 2500
multiScoreThreshold = 5

def poisson_pdf(k,l):
    return (l**k)*np.exp(-l)/misc.factorial(k)

# Specify the facility
state = {}
state['Facility'] = 'FLASH'
# Specify folders with frms6 and darkcal data
state['FLASH/DataRe'] = "/data/beamline/current/raw/pnccd/block-03/holography_.+_.+_([0-9]{4})_.+.frms6"
state['FLASH/DataGlob'] = "/data/beamline/current/raw/pnccd/block-03/holography_*_*_*_*.frms6"
state['FLASH/CalibGlob'] = "/data/beamline/current/processed/calib/block-03/*.darkcal.h5"
state['FLASH/DAQFolder'] = "/asap3/flash/gpfs/bl1/2017/data/11001733/processed/daq"
state['FLASH/MotorFolder'] = '/home/tekeberg/Beamtimes/Holography2017/motor_positions/motor_data.data'
state['FLASH/DAQBaseDir'] = "/data/beamline/current/raw/hdf/block-03/exp2/"
state['do_offline'] = False
state['online_start_from_run'] = 245
#state['FLASH/ProcessingRate'] = 1

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
        detector = analysis.pixel_detector.moveHalf(evt, detector, horizontal=int(gap_total/pixel_size), outkey='data_half-moved')
        mask_center_s = analysis.pixel_detector.moveHalf(evt, add_record(evt["analysis"], "analysis", "mask", mask_center), horizontal=int(gap_total/pixel_size), outkey='mask_half-moved').data
        detector_type = "analysis"
        detector_key  = "data_half-moved"
    # Do basic hitfinding using lit pixels
    analysis.hitfinding.countLitPixels(evt, evt[detector_type][detector_key], 
                                       aduThreshold=aduThreshold, 
                                       hitscoreThreshold=hitScoreThreshold, mask=mask_center_s)

    hit = bool(evt["analysis"]["litpixel: isHit"].data)
    strong_hit=evt["analysis"]["litpixel: hitscore"].data>strong_hit_threshold
    plotting.line.plotHistory(add_record(evt["analysis"],"analysis","total ADUs", evt[detector_type][detector_key].data.sum()),
                              label='Total ADU', hline=hitScoreThreshold, group='Metric', history=1000)
    
    plotting.line.plotHistory(evt["analysis"]["litpixel: hitscore"],
                              label='Nr. of lit pixels', hline=hitScoreThreshold, group='Metric',
                              history=1000)
    analysis.hitfinding.hitrate(evt, hit, history=50)

    plotting.line.plotHistory(add_record(evt["analysis"], "analysis", "is_hit", hit),
                              label='Is hit', group='Metric',
                              history=1000)


    is_strong_hit = evt["analysis"]["total ADUs"].data > 1e6
    
    if hit and is_strong_hit:
        plotting.image.plotImage(evt[detector_type][detector_key], name="pnCCD (Very Strong)", group='Images', mask=mask_center_s)

    
    if scanInjector:
        plotting.histogram.plotNormalizedHistogram(evt["motorPositions"]["InjectorX"], float(1 if hit else 0), hmin=scanXmin, hmax=scanXmax, bins=scanXbins, name="Histogram: InjectorX x Hitrate", group="Scan injector pos", buffer_length=1000)
        plotting.histogram.plotNormalizedHistogram(evt["motorPositions"]["InjectorZ"], float(1 if hit else 0), hmin=scanZmin, hmax=scanZmax, bins=scanZbins, name="Histogram: InjectorZ x Hitrate", group="Scan injector pos", buffer_length=1000)
        plotting.histogram.plotNormalizedHistogram(evt["motorPositions"]["ManualY"], float(1 if hit else 0), hmin=scanYmin, hmax=scanYmax, bins=scanYbins, name="Histogram: ManualY x Hitrate", group="Scan injector pos", buffer_length=1000)

        plotting.histogram.plotNormalizedHistogram(evt["motorPositions"]["InjectorSamplePressure"], float(1 if hit else 0), hmin=50, hmax=300, bins=50, name="Histogram: InjectorSamplePressure x Hitrate", group="Scan injector pressure", buffer_length=1000)
        plotting.histogram.plotNormalizedHistogram(evt["motorPositions"]["InjectorNozzlePressure"], float(1 if hit else 0), hmin=50, hmax=300, bins=50, name="Histogram: InjectorNozzlePressure x Hitrate", group="Scan injector pressure", buffer_length=1000)
        plotting.histogram.plotNormalizedHistogram(evt["motorPositions"]["InjectorFocusingGas"], float(1 if hit else 0), hmin=50, hmax=300, bins=50, name="Histogram: InjectorFocusingGas x Hitrate", group="Scan injector pressure", buffer_length=1000)
        plotting.histogram.plotNormalizedHistogram(evt["motorPositions"]["InjectorPressure"], float(1 if hit else 0), hmin=50, hmax=300, bins=50, name="Histogram: InjectorPressure x Hitrate", group="Scan", buffer_length=1000)


        plotting.correlation.plotScatter(evt["motorPositions"]["InjectorX"], evt['analysis']['litpixel: hitscore'], 
                                         name='InjectorX vs Hitscore', xlabel='InjectorX', ylabel='Hit Score',
                                         group='Scan injector pos')
        plotting.correlation.plotScatter(evt["motorPositions"]["InjectorZ"], evt['analysis']['litpixel: hitscore'], 
                                         name='InjectorZ vs Hitscore', xlabel='InjectorZ', ylabel='Hit Score',
                                         group='Scan injector pos')
        plotting.correlation.plotScatter(evt["motorPositions"]["ManualY"], evt['analysis']['litpixel: hitscore'], 
                                         name='ManualY vs Hitscore', xlabel='ManualY', ylabel='Hit Score',
                                         group='Scan injector pos')

        plotting.correlation.plotScatter(evt["motorPositions"]["InjectorSamplePressure"], evt['analysis']['litpixel: hitscore'], 
                                         name='InjectorSamplePressure vs Hitscore',
                                         xlabel='InjectorSamplePressure', ylabel='Hit Score',
                                         group='Scan injector pressure')
        plotting.correlation.plotScatter(evt["motorPositions"]["InjectorNozzlePressure"], evt['analysis']['litpixel: hitscore'], 
                                         name='InjectorNozzlePressure vs Hitscore',
                                         xlabel='InjectorNozzlePressure', ylabel='Hit Score',
                                         group='Scan injector pressure')
        plotting.correlation.plotScatter(evt["motorPositions"]["InjectorFocusingGas"], evt['analysis']['litpixel: hitscore'], 
                                         name='InjectorFocusingGas vs Hitscore',
                                         xlabel='InjectorFocusingGas', ylabel='Hit Score',
                                         group='Scan injector presssure')
        plotting.correlation.plotScatter(evt["motorPositions"]["InjectorPressure"], evt['analysis']['litpixel: hitscore'], 
                                         name='InjectorPressure vs Hitscore',
                                         xlabel='InjectorPressure', ylabel='Hit Score',
                                         group='Scan injector pressure')
        plotting.line.plotHistory(evt["motorPositions"]["InjectorX"], label="InjectorX", group="Scan injector pos")
        plotting.line.plotHistory(evt["motorPositions"]["InjectorZ"], label="InjectorZ", group="Scan injector pos")

    if outputEveryImage:
        plotting.image.plotImage(evt[detector_type][detector_key], name="pnCCD (All)", group='Images', mask=mask_center_s)

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
        plotting.image.plotImage(evt[detector_type][detector_key], name="pnCCD (log Hits)", group='Images',
                                 mask=mask_center_s, log=True)
        plotting.image.plotImage(evt[detector_type][detector_key], name="pnCCD (Hits)", group='Images',
                                 mask=mask_center_s, log=False)
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
                        

            if correctsized_hit:
                # Plot Correct sized hits
                plotting.image.plotImage(evt[detector_type][detector_key], group='Sizing', msg=msg, name="pnCCD front (correct hit)", mask=mask_center_fit_s)
                if strong_hit:
                    plotting.image.plotImage(evt[detector_type][detector_key], group='Sizing', msg=msg, name="pnCCD front (correct and strong hit)", mask=mask_center_fit_s)
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


    if hit and do_patterson:
        analysis.patterson.patterson(evt, detector_type, detector_key, mask_center_s, 
                                     threshold=patterson_threshold,
                                     diameter_pix=patterson_diameter,
                                     xgap_pix=patterson_xgap_pix,
                                     ygap_pix=patterson_ygap_pix,
                                     frame_pix=patterson_frame_pix,
                                     crop=512, full_output=True, **patterson_params)
        plotting.line.plotHistory(evt["analysis"]["multiple score"], history=1000, name='Multiscore', group='Holography', hline=multiScoreThreshold)
        #print evt["analysis"]["multiple score"].data, multiScoreThreshold
        multiple_hit = evt["analysis"]["multiple score"].data > multiScoreThreshold
        if multiple_hit:
            plotting.image.plotImage(evt["analysis"]["patterson"], group="Holography", name="Patterson (multiple hits)")
            plotting.image.plotImage(evt["analysis"]["patterson multiples"], group="Holography", name="Patterson mask (multiple hits)")
            plotting.image.plotImage(evt[detector_type][detector_key], group="Holography", name="Multiple hits (image)", mask=mask_center_s)
            analysis.refocus_hologram.refocus_hologram_evt(evt,detector_type,detector_key) 
            plotting.image.plotImage(evt["analysis"]["focused_CC"], group="Holography", name="refocused Hologram (image)")
        else:
            plotting.image.plotImage(evt["analysis"]["patterson"], group="Holography", name="Patterson (non-multiple hits)")  
    
    if not hit and do_patterson:
        multiple_hit = False
    if do_patterson:
        analysis.hitfinding.hitrate(evt, multiple_hit, history=50, outkey='multiple_hitrate')
        
        if scanInjector:
            plotting.histogram.plotNormalizedHistogram(evt["motorPositions"]["InjectorX"], float(1 if multiple_hit else 0), hmin=scanXmin, hmax=scanXmax, bins=scanXbins, name="Histogram: InjectorX x Multiple hitrate", group="Scan injector pos", buffer_length=1000)
            plotting.histogram.plotNormalizedHistogram(evt["motorPositions"]["InjectorZ"], float(1 if multiple_hit else 0), hmin=scanZmin, hmax=scanZmax, bins=scanZbins, name="Histogram: InjectorZ x Multiple hitrate", group="Scan injector pos", buffer_length=1000)


        if ipc.mpi.is_main_worker():
            plotting.line.plotHistory(evt["analysis"]["multiple_hitrate"], label='Multiple Hit rate [%]', group='Metric', history=10000)


            non_hitrate = 1. - (evt["analysis"]["hitrate"].data / 100.)
            multi_hitrate = (evt["analysis"]["multiple_hitrate"].data / 100.)
            hitrate_corrected_poisson = multi_hitrate / (0.25 * np.exp(-2.) * non_hitrate *  np.log(non_hitrate)**2)
            #print "%f/%f/%.4f" %(non_hitrate,multi_hitrate,hitrate_corrected_poisson)
            e = add_record(evt['analysis'], "analysis", "multiple hitrate (corrected)", hitrate_corrected_poisson)
            plotting.line.plotHistory(e, label='Multiple hitrate (poisson corrected)', group='Holography', history=10000)
