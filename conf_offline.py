# Import analysis/plotting modules
import analysis.event
import analysis.hitfinding
import plotting.image
import plotting.line
import plotting.correlation
import plotting.histogram
import utils.cxiwriter
import ipc
from backend.record import add_record
import numpy as np
import time, os, sys

# Commandline arguments
from utils.cmdline_args import argparser, add_config_file_argument
add_config_file_argument('--hitscore-threshold', metavar='INT',
                         help='Hitscore threshold', type=int)
add_config_file_argument('--run-nr', metavar='INT',
                         help='Run number', type=int, required=True)
add_config_file_argument('--dark-nr', metavar='INT',
                         help='Run number of dark', type=int, required=True)
add_config_file_argument('--output-level', type=int, 
                         help='Output level (1: small data for all events, 2: tof data for hits, 3: pnccd data for hits',
                         default=3)
args = argparser.parse_args()

# Save data to file
do_write=True

# Send plots when doing injector scans
scanInjector = False
scanXmin  = 0
scanXmax  = 10
scanXbins = 20
scanZmin  = 0
scanZmax  = 10
scanZbins = 20

# Send every image
outputEveryImage = False

# Quick config parameters
if args.hitscore_threshold:
    hitScoreThreshold = args.hitscore_threshold
else:
    hitScoreThreshold = 5000
aduThreshold = 200

# Path to rawdata
base_path = '/asap3/flash/gpfs/bl1/2017/data/11001733/' 

# Specify the facility
state = {}
state['Facility'] = 'FLASH'
# Specify folders with frms6 and darkcal data
state['FLASH/DataGlob']    = base_path + "raw/pnccd/block-*/holography_*_2017*_%04d_*.frms6" %args.run_nr
state['FLASH/CalibGlob']   = base_path + "processed/calib/block-*/calib_*_%04d.darkcal.h5"   %args.dark_nr
state['FLASH/DAQFolder']   = base_path + "processed/daq/"
state['FLASH/DAQBaseDir']  = base_path + "raw/hdf/block-01/exp2/"
state['FLASH/MotorFolder'] = '/home/tekeberg/Beamtimes/Holography2017/motor_positions/motor_data.data'
state['do_offline'] = True
state['reduce_nr_event_readers'] = 1
#state['FLASH/ProcessingRate'] = 1

# Output directory
w_dir = base_path + "processed/hummingbird/"

# Output levels
level = args.output_level
save_anything = level > 0
save_tof = level >= 2                                                                                                      
save_pnccd = level >= 3 

def beginning_of_run():
    global W
    W = utils.cxiwriter.CXIWriter(w_dir + "/r%04d_ol%d.h5" %(args.run_nr, level), chunksize=10)

def calculate_epoch_times(evt, time_sec, time_usec):
    add_record(evt['ID'], 'ID', 'time', time_sec.data + 1.e-6*time_usec.data)
    #add_record(evt['ID'], 'ID', 'timeAgo', time.time() - (time_sec.data + 1.e-6*time_usec.data))
    # Calculating timeAgo with 606 second offset due to miscalibration of pnCCD server clock
    #add_record(evt['ID'], 'ID', 'timeAgo', -606. + time.time() - (time_sec.data + 1.e-6*time_usec.data))
    add_record(evt['ID'], 'ID', 'timeAgo', 0. + time.time() - (time_sec.data + 1.e-6*time_usec.data))

# Counter
counter = -1

# This function is called for every single event
# following the given recipe of analysis
def onEvent(evt):

    # Increment the counter
    global counter
    counter += 1

    # Processing rate [Hz]
    analysis.event.printProcessingRate()

    # Read ToF traces
    try:
        tof = evt["DAQ"]["TOF"]
    except RuntimeError:
        tof = None

    # Read FEL parameters
    try:
        wavelength_nm = evt['FEL']['wavelength'].data
        gmd = evt['FEL']['gmd'].data
    except RuntimeError:
        wavelength_nm = np.nan
        gmd = np.nan

    if tof is not None:
        plotting.line.plotTrace(tof, label='TOF Trace', group="TOF", history=10000)

    # Do basic hitfinding using lit pixels
    analysis.hitfinding.countLitPixels(evt, evt["photonPixelDetectors"]["pnCCD"], 
                                       aduThreshold=aduThreshold, 
                                       hitscoreThreshold=hitScoreThreshold,
                                       hitscoreMax=400000 )

    hit = bool(evt["analysis"]["litpixel: isHit"].data)
    plotting.line.plotHistory(evt["analysis"]["litpixel: hitscore"],
                              label='Nr. of lit pixels', hline=hitScoreThreshold, group='Metric')
    analysis.hitfinding.hitrate(evt, hit, history=5000)

    if scanInjector:
        plotting.histogram.plotNormalizedHistogram(evt["motorPositions"]["InjectorX"], float(1 if hit else 0), hmin=scanXmin, hmax=scanXmax, bins=scanXbins, name="Histogram: InjectorX x Hitrate", group="Scan", buffer_length=1000)
        plotting.histogram.plotNormalizedHistogram(evt["motorPositions"]["InjectorZ"], float(1 if hit else 0), hmin=scanZmin, hmax=scanZmax, bins=scanZbins, name="Histogram: InjectorZ x Hitrate", group="Scan", buffer_length=1000)

        plotting.correlation.plotScatter(evt["motorPositions"]["InjectorX"], evt['analysis']['litpixel: hitscore'], 
                                         name='InjectorX vs Hitscore', xlabel='InjectorX', ylabel='Hit Score',
                                         group='Scan')
        plotting.correlation.plotScatter(evt["motorPositions"]["InjectorZ"], evt['analysis']['litpixel: hitscore'], 
                                         name='InjectorZ vs Hitscore', xlabel='InjectorZ', ylabel='Hit Score',
                                         group='Scan')
        
    if outputEveryImage:
        plotting.image.plotImage(evt['photonPixelDetectors']['pnCCD'], name="pnCCD (All)", group='Images')
    if ipc.mpi.is_main_worker():
        plotting.line.plotHistory(evt["analysis"]["hitrate"], label='Hit rate [%]', group='Metric', history=10000)
    if hit:
        plotting.image.plotImage(evt['photonPixelDetectors']['pnCCD'], name="pnCCD (Hits)", group='Images')

    if do_write:
        if hit and save_anything:
            D = {}
            D['entry_1'] = {}
            if save_pnccd:
                D['entry_1']['detector_1'] = {}
            if save_tof:
                D['entry_1']['detector_2'] = {}
            D['entry_1']['event'] = {}
            D['entry_1']['injector'] = {}
            D['entry_1']['FEL'] = {}
            D['entry_1']['result_1'] = {}

            # PNCCD
            if save_pnccd:
                D['entry_1']['detector_1']['data'] = numpy.asarray(evt["photonPixelDetectors"]["pnCCD"].data, dtype='float16')
                # TODO: Save mask and gain
        
            # TOF
            if save_tof and tof:
                D['entry_1/']['detector_2'] = tof
            
            # FEL PARAMETERS
            D['entry_1']['FEL']['gmd'] = gmd
            D['entry_1']['FEL']['wavelength_nm'] = wavelength_nm

            # HIT PARAMETERS
            D['entry_1']['result_1']['hitscore_litpixel'] = evt['analysis']['litpixel: hitscore'].data
            D['entry_1']['result_1']['hitscore_litpixel_threshold'] = hitScoreThreshold
        
            # EVENT IDENTIFIERS
            D['entry_1']['event']['bunch_id']   = evt['ID']['BunchID'].data
            D['entry_1']['event']['tv_sec']     = evt['ID']['tv_sec'].data
            D['entry_1']['event']['tv_usec']    = evt['ID']['tv_usec'].data
            D['entry_1']['event']['dataset_id'] = evt['ID']['DataSetID'].data
            D['entry_1']['event']['bunch_sec']  = evt['ID']['bunch_sec'].data 
        
            # TODO: INJECTOR
            # TODO: FEL
            W.write_slice(D)

def end_of_run():
    #W.close(barrier=True)
    W.close()
    if ipc.mpi.is_main_event_reader():
        print "Clean exit"
