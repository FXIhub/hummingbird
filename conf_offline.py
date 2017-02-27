# Import analysis/plotting modules
import analysis.event
import analysis.hitfinding
import analysis.pixel_detector
import plotting.image
import plotting.line
import plotting.correlation
import plotting.histogram
import utils.cxiwriter
import utils.reader
import ipc
from backend.record import add_record
import numpy as np
import time, os, sys
import h5py

this_dir = os.path.dirname(os.path.realpath(__file__))                                                                             
sys.path.append(this_dir)
import params

# Commandline arguments
from utils.cmdline_args import argparser, add_config_file_argument
add_config_file_argument('--hitscore-threshold', metavar='INT',
                         help='Hitscore threshold', type=int)
add_config_file_argument('--run-nr', metavar='INT',
                         help='Run number', type=int, required=True)
add_config_file_argument('--dark-nr', metavar='INT',
                         help='Run number of dark', type=int)
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

# Geometry
move_half = True

# Read in parameters from a csv file
p = params.read_params('params.csv', args.run_nr)

# Detector params
detector_distance = 220e-03
gap_top=2.8e-03
gap_bottom=3.1e-03
gap_total=gap_top+gap_bottom
ny=1024
nx=1024
pixel_size=7.5e-05
center_shift=int((gap_top-gap_bottom)/pixel_size)

# Quick config parameters
if args.hitscore_threshold:
    hitScoreThreshold = args.hitscore_threshold
else:
    hitScoreThreshold = p['hitscoreThreshold']
aduThreshold = 200

# Dark file
if args.dark_nr:
    darkfile_nr = args.dark_nr
else:
    darkfile_nr = p['darkNr']

# Path to rawdata
base_path = '/asap3/flash/gpfs/bl1/2017/data/11001733/' 

# Specify the facility
state = {}
state['Facility'] = 'FLASH'
# Specify folders with frms6 and darkcal data
state['FLASH/DataGlob']    = base_path + "raw/pnccd/block-*/holography_*_2017*_%04d_*.frms6" %args.run_nr
state['FLASH/CalibGlob']   = base_path + "processed/calib/block-*/calib_*_%04d.darkcal.h5"   %darkfile_nr
state['FLASH/DAQFolder']   = base_path + "processed/daq/"
state['FLASH/DAQBaseDir']  = base_path + "raw/hdf/block-02/exp2/"
state['FLASH/MotorFolder'] = '/home/tekeberg/Beamtimes/Holography2017/motor_positions/motor_data.data'
state['do_offline'] = True
state['reduce_nr_event_readers'] = 1
#state['FLASH/ProcessingRate'] = 1

# Mask
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

# Output levels
level = args.output_level
save_anything = level > 0
save_tof = level >= 2                                                                                                      
save_pnccd = level >= 3 

# Output directory
w_dir = base_path + "processed/hummingbird/"
filename_tmp  = w_dir + "/.r%04d_ol%d.h5" %(args.run_nr, level)
filename_done = w_dir + "/r%04d_ol%d.h5" %(args.run_nr, level)
D_solo = {}

def beginning_of_run():
    global W
    W = utils.cxiwriter.CXIWriter(filename_tmp, chunksize=10)

# This function is called for every single event
# following the given recipe of analysis
def onEvent(evt):

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

    # PNCCD
    detector_type = "photonPixelDetectors"
    detector_key  = "pnCCD"
    detector = evt[detector_type][detector_key]

    if move_half:
        detector_s = analysis.pixel_detector.moveHalf(evt, detector, horizontal=int(gap_total/pixel_size), outkey='data_half-moved')
        mask_center_s = analysis.pixel_detector.moveHalf(evt, add_record(evt["analysis"], "analysis", "mask", mask_center), 
                                                         horizontal=int(gap_total/pixel_size), outkey='mask_half-moved').data
        detector_type = "analysis"
        detector_key  = "data_half-moved"
        detector = evt[detector_type][detector_key]
    else:
        mask_center_s = mask_center

    # Do basic hitfinding using lit pixels
    analysis.hitfinding.countLitPixels(evt, detector,
                                       aduThreshold=aduThreshold, 
                                       hitscoreThreshold=hitScoreThreshold,
                                       mask=mask_center_s)

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
                D['entry_1']['detector_1']['data'] = np.asarray(detector.data, dtype='float16')
                if ipc.mpi.is_main_event_reader() and len(D_solo) == 0:
                    bitmask = np.array(mask_center_s, dtype='uint16')
                    bitmask[bitmask==0] = 512
                    bitmask[bitmask==1] = 0
                    D_solo["entry_1"] = {}
                    D_solo["entry_1"]["detector_1"] = {}
                    D_solo["entry_1"]["detector_1"]["mask"]= bitmask
        
            # TOF
            if save_tof and tof:
                D['entry_1/']['detector_2']['data'] = tof
            
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
    if ipc.mpi.is_main_event_reader():
        if 'entry_1' not in D_solo:
            D_solo["entry_1"] = {}
        W.write_solo(D_solo)
    #W.close(barrier=True)
    W.close()
    if ipc.mpi.is_main_event_reader():
        with h5py.File(filename_tmp, 'a') as f:
            if save_pnccd:
                f['entry_1/data_1'] = h5py.SoftLink('/entry_1/detector_1')
                f['entry_1/detector_1/data'].attrs['axes'] = ['experiment_identifier:y:x']
            if save_tof:
                f['entry_1/data_2'] = h5py.SoftLink('/entry_1/detector_2')
                #f['entry_1/detector_2/data'].attrs['axes'] = ['experiment_identifier:x']
            print "Successfully created soft links and attributes"
        os.system('mv %s %s' %(filename_tmp, filename_done))
        os.system('chmod 770 %s' %(filename_done))
        print "Moved temporary file %s to %s" %(filename_tmp, filename_done)
        print "Clean exit"

