# Import analysis/plotting modules
import analysis.event
import analysis.hitfinding
import analysis.pixel_detector
import plotting.image
import plotting.line
import plotting.correlation
import plotting.histogram
from backend.record import add_record
import numpy as np
import time
import ipc

scanInjector = False
scanXmin = 88
scanXmax = 100
scanXbins = 220/2
scanZmin = 88
scanZmax = 100
scanZbins = 220/2

outputEveryImage = False
do_sizing = False
move_half = True

#Detector params
detector_distance = 220e-03
gap_top=2.8e-03
gap_bottom=3.1e-03
gap_total=gap_top+gap_bottom
ny=1024
nx=1024


pixel_size=7.5e-05
# Quick config parameters
# hitScoreThreshold = 9000
# aduThreshold = 200
hitScoreThreshold = 25000
aduThreshold = 200

# Specify the facility
state = {}
state['Facility'] = 'FLASH'
# Specify folders with frms6 and darkcal data
state['FLASH/DataGlob'] = "/data/beamline/current/raw/pnccd/block-01/holography*0023*.frms6"
state['FLASH/CalibGlob'] = "/data/beamline/current/processed/calib/block-01/*.darkcal.h5"
state['FLASH/DAQFolder'] = "/asap3/flash/gpfs/bl1/2017/data/11001733/processed/daq/"
state['FLASH/MotorFolder'] = '/home/tekeberg/Beamtimes/Holography2017/motor_positions/motor_data.data'
state['do_offline'] = True
#state['FLASH/ProcessingRate'] = 1

#Mask
#Mask out center
mask_center=np.ones((ny, nx), dtype=np.bool)
radius=30
cx=0
cy=0
xx,yy=np.meshgrid(np.arange(nx), np.arange(ny))
rr=(xx-nx/2)**2+(yy-ny/2)**2 >= (radius**2)
mask_center &= rr

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
                                       hitscoreThreshold=hitScoreThreshold)

    hit = bool(evt["analysis"]["litpixel: isHit"].data)
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
            # Sizing
            # ------
            binning = 4
            
            centerParams = {
                'x0'       : (512 + 10 - (nx_front-1)/2.)/binning,
                'y0'       : (512 + 20 - (ny_front-1)/2.)/binning,
                'maxshift' : int(numpy.ceil(10./binning)),
                'threshold': 1,
                #'threshold': 20*binning**2,
                'blur'     : 4,
            }
            pixelsize_native = 75E-6 
            modelParams = {'wavelength': 5.2, 
                           'pixelsize': 7.5e-05,
                           'distance': 220., 
                           'material': 'sucrose'}
            sizingParams = {'d0':200., # in nm
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
            diameter_min = 50  #[nm]
            diameter_max = 150 #[nm]
            
            # Patterson
            # ---------
            patterson_threshold = 5.
            patterson_floor_cut = 50.
            patterson_mask_smooth = 5.
            patterson_diameter = 60. #4 * expected_diameter * 1E-9 / res
            multiple_score_threshold = 200.



    #time.sleep(0.05)
