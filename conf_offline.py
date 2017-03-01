# Import analysis/plotting modules
import analysis.event
import analysis.hitfinding
import analysis.pixel_detector
import analysis.patterson
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

# Path to rawdata
base_path = '/asap3/flash/gpfs/bl1/2017/data/11001733/' 

#import h5writer
#h5writer.logger.setLevel("DEBUG")

# Commandline arguments
from utils.cmdline_args import argparser, add_config_file_argument
add_config_file_argument('--hitscore-threshold', metavar='INT',
                         help='Hitscore threshold', type=int)
add_config_file_argument('--multiscore-threshold', metavar='INT',
                         help='Multiscore threshold', type=int)
add_config_file_argument('--run-nr', metavar='INT',
                         help='Run number', type=int, required=True)
add_config_file_argument('--dark-nr', metavar='INT',
                         help='Run number of dark', type=int)
add_config_file_argument('--output-level', type=int, 
                         help='Output level (1: small data for all events, 2: tof data for hits, \
                               3: pnccd data for hits, 4: all data for multiple hits)',
                         default=3)
add_config_file_argument('--outdir', metavar='STR',
                         help='output directory different from default (optional)', type=str)
add_config_file_argument('--nr-frames', type=int, 
                         help='Number of frames', default=None)
add_config_file_argument('--skip-tof', action='store_true')
args = argparser.parse_args()

# Save data to file
do_write=True

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

# Hitscore threshold
if args.hitscore_threshold is not None:
    hitScoreThreshold = args.hitscore_threshold
else:
    hitScoreThreshold = p['hitscoreThreshold']
aduThreshold = 200

# Multiscore threshold
if args.multiscore_threshold is not None:
    multiScoreThreshold = args.multiscore_threshold
else:
    multiScoreThreshold = p['multiscoreThreshold']

# Dark file
if args.dark_nr:
    darkfile_nr = args.dark_nr
else:
    darkfile_nr = p['darkNr']

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
state['online_start_from_run'] = False
state['reduce_nr_event_readers'] = 1
#state['FLASH/ProcessingRate'] = 1

# Mask
Mask = utils.reader.MaskReader("/asap3/flash/gpfs/bl1/2017/data/11001733/processed/mask_v3.h5", "/data")
mask = Mask.boolean_mask
mask_center=np.ones((ny, nx), dtype=np.bool)
radius=30
cx=0
cy=0
xx,yy=np.meshgrid(np.arange(nx), np.arange(ny))
rr=(xx-nx/2)**2+(yy-ny/2)**2 >= (radius**2)
mask_center &= rr
mask_center &= mask

# Patterson
patterson_threshold = 3.
patterson_params = {
    "floor_cut" : 50.,
    "mask_smooth" : 5.,
    "darkfield_x" : 130,
    "darkfield_y" : 130,
    "darkfield_sigma" : 30.,
    "darkfield_N" : 4,
}
patterson_diameter = 50.

# Output levels
level = args.output_level
save_anything = level > 0
save_tof = level >= 2 and not args.skip_tof                                                                                                      
save_pnccd = level >= 3
save_multiple = level >= 4

# Output directory
if args.outdir is None:
    w_dir = base_path + "processed/hummingbird/"
else:
    w_dir = args.outdir
filename_tmp  = w_dir + "/.r%04d_ol%d.h5" %(args.run_nr, level)
filename_done = w_dir + "/r%04d_ol%d.h5" %(args.run_nr, level)
D_solo = {}

# Counter
counter = -1

def beginning_of_run():
    global W
    W = utils.cxiwriter.CXIWriter(filename_tmp, chunksize=10)

# This function is called for every single event
# following the given recipe of analysis
def onEvent(evt):

    # Counter
    global counter
    counter += 1

    # Option to stop after fixed number of frames
    if args.nr_frames is not None:
        #print counter, args.nr_frames/ipc.mpi.nr_event_readers()
        if (counter == args.nr_frames/ipc.mpi.nr_event_readers()):
            raise StopIteration

    # Processing rate [Hz]
    analysis.event.printProcessingRate()

    # Read ToF traces
    try:
        tof = evt["DAQ"]["TOF"]
    except RuntimeError:
        tof = None
    except KeyError:
        tof = None

    # Read FEL parameters
    try:
        wavelength_nm = evt['FEL']['wavelength'].data
        gmd = evt['FEL']['gmd'].data
    except RuntimeError:
        wavelength_nm = np.nan
        gmd = np.nan

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
    hitscore = evt['analysis']['litpixel: hitscore'].data

    # Find multiple hits based on patterson function
    if hit and save_multiple:
        analysis.patterson.patterson(evt, "analysis", "data_half-moved", mask_center_s, 
                                     threshold=patterson_threshold,
                                     diameter_pix=patterson_diameter,
                                     crop=512, full_output=True, **patterson_params)
        #print evt['analysis'].keys()
        multiple_hit = evt["analysis"]["multiple score"].data > multiScoreThreshold

    # Write to file
    if do_write:
        if hit and save_anything:
            D = {}
            D['entry_1'] = {}
            if save_pnccd:
                D['entry_1']['detector_1'] = {}
            if save_tof:
                D['entry_1']['detector_2'] = {}
            D['entry_1']['event'] = {}
            D['entry_1']['motors'] = {}
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
            
            # PATTERSON
            if save_multiple:
                D['entry_1']['detector_1']['patterson'] = np.asarray(evt['analysis']['patterson'].data, dtype='float16') 

            # TOF
            if save_tof and tof:
                D['entry_1']['detector_2']['data'] = tof.data
            
            # FEL PARAMETERS
            D['entry_1']['FEL']['gmd'] = gmd
            D['entry_1']['FEL']['wavelength_nm'] = wavelength_nm

            # HIT PARAMETERS
            D['entry_1']['result_1']['hitscore_litpixel'] = evt['analysis']['litpixel: hitscore'].data
            D['entry_1']['result_1']['hitscore_litpixel_threshold'] = hitScoreThreshold
            if save_multiple:
                D['entry_1']['result_1']['multiscore_patterson'] = evt['analysis']['multiple score'].data
                D['entry_1']['result_1']['multiscore_patterson_threshold'] = multiScoreThreshold
        
            # EVENT IDENTIFIERS
            D['entry_1']['event']['bunch_id']   = evt['ID']['BunchID'].data
            D['entry_1']['event']['tv_sec']     = evt['ID']['tv_sec'].data
            D['entry_1']['event']['tv_usec']    = evt['ID']['tv_usec'].data
            D['entry_1']['event']['dataset_id'] = evt['ID']['DataSetID'].data
            D['entry_1']['event']['bunch_sec']  = evt['ID']['bunch_sec'].data 
        
            # MOTORS
            D['entry_1']['motors']['manualy']       = evt['motorPositions']['ManualY'].data
            D['entry_1']['motors']['injectorx']     = evt['motorPositions']['InjectorX'].data
            D['entry_1']['motors']['injectory']     = evt['motorPositions']['InjectorZ'].data
            D['entry_1']['motors']['trigdelay']     = evt['motorPositions']['TrigDelay'].data
            D['entry_1']['motors']['samplepress']   = evt['motorPositions']['InjectorSamplePressure'].data
            D['entry_1']['motors']['nozzlepress']   = evt['motorPositions']['InjectorNozzlePressure'].data
            D['entry_1']['motors']['posdownstream'] = evt['motorPositions']['PosDownstream'].data
            D['entry_1']['motors']['posupstream']   = evt['motorPositions']['PosUpstream'].data
            D['entry_1']['motors']['injectorpress'] = evt['motorPositions']['InjectorPressure'].data
            D['entry_1']['motors']['focusinggas']   = evt['motorPositions']['InjectorFocusingGas'].data
            
            # TODO: FEL
            W.write_slice(D)

def end_of_run():
    if ipc.mpi.is_main_event_reader():
        if 'entry_1' not in D_solo:
            D_solo["entry_1"] = {}
        W.write_solo(D_solo)
    W.close(barrier=True)
    #W.close()
    if ipc.mpi.is_main_event_reader():
        with h5py.File(filename_tmp, 'a') as f:
            if save_pnccd and '/entry_1/detector_1' in f:
                f['entry_1/data_1'] = h5py.SoftLink('/entry_1/detector_1')
                f['entry_1/detector_1/data'].attrs['axes'] = ['experiment_identifier:y:x']
                n_frames = (len(f['/entry_1/data_1/data']))
            else:
                n_frames = 0
            print "Counting in total %i frames." % n_frames
            if save_multiple and 'entry_1/detector_1/patterson' in f:
                f['entry_1/detector_1/patterson'].attrs['axes'] = ['experiment_identifier:y:x']
            if save_tof and '/entry_1/detector_2' in f:
                f['entry_1/data_2'] = h5py.SoftLink('/entry_1/detector_2')
                #f['entry_1/detector_2/data'].attrs['axes'] = ['experiment_identifier:x']
            print "Successfully created soft links and attributes"
        os.system('mv %s %s' %(filename_tmp, filename_done))
        os.system('chmod 770 %s' %(filename_done))
        print "Moved temporary file %s to %s" %(filename_tmp, filename_done)
        print "Clean exit"

