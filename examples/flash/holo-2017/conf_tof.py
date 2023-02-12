import os
import re
import time

import numpy as np

# Import analysis/plotting modules
from hummingbird import analysis, ipc, plotting, utils
from hummingbird.backend.record import add_record

scanInjector = False
scanXmin = -250
scanXmax = 250
scanXbins = 500
scanZmin = 88
scanZmax = 100
scanZbins = 220/2
scanYmin = 94
scanYmax = 97
scanYbins = 20

outputEveryImage = True
do_sizing = False
do_write = False
do_showhybrid = False
move_half = True

#Detector params
detector_distance = 220e-03
gap_top=0.8e-03
gap_bottom=3.0e-03
gap_total=gap_top+gap_bottom
ny=1024
nx=1024
pixel_size=7.5e-05

center_shift=int((gap_top-gap_bottom)/pixel_size)

# Quick config parameters
hitScoreThreshold = 13000
aduThreshold = 200
strong_hit_threshold = 60000

#experiment_folder = "/data/beamline/current"
experiment_folder = "/asap3/flash/gpfs/bl1/2017/data/11001733"

# Specify the facility
state = {}
state['Facility'] = 'FLASH'
# Specify folders with frms6 and darkcal data
state['FLASH/DataGlob'] = os.path.join(experiment_folder, "raw/pnccd/block-02/holography_*_*_*_*.frms6")
state['FLASH/DataRe'] = os.path.join(experiment_folder, "raw/pnccd/block-02/holography_.+_.+_([0-9]{4})_.+.frms6")
#state['FLASH/DataGlob'] = os.path.join(experiment_folder, "raw/pnccd/block-02/holography_*_*_*_*.frms6")
state['FLASH/CalibGlob'] = os.path.join(experiment_folder, "processed/calib/block-02/*.darkcal.h5")
state['FLASH/DAQFolder'] = "/asap3/flash/gpfs/bl1/2017/data/11001733/processed/daq"
state['FLASH/MotorFolder'] = '/home/tekeberg/Beamtimes/Holography2017/motor_positions/motor_data.data'
state['FLASH/DAQBaseDir'] = os.path.join(experiment_folder, "raw/hdf/block-02")
state['do_offline'] = True
state['online_start_from_run'] = False
#state['FLASH/ProcessingRate'] = 1



#Mask
Mask = utils.reader.MaskReader("/asap3/flash/gpfs/bl1/2017/data/11001733/processed/mask_v1.h5", "/data")
mask = Mask.boolean_mask

#Mask out center
mask_center=np.ones((ny, nx), dtype=np.bool)
radius=30
#radius=70
cx=0
cy=0
xx,yy=np.meshgrid(np.arange(nx), np.arange(ny))
rr=(xx-nx/2)**2+(yy-ny/2)**2 >= (radius**2)
mask_center &= rr
mask_center &= mask

# Sizing parameters
# ------
binning = 4

centerParams = {'x0'       : (512 - (nx-1)/2.)/binning,
                'y0'       : (512 + center_shift -(ny-1)/2.)/binning,
                'maxshift' : int(np.ceil(10./binning)),
                'threshold': 1,
                'blur'     : 4}

modelParams = {'wavelength': 5.3, #in nm
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


def beginning_of_run():
    if do_write:
        global W
        W = utils.cxiwriter.CXIWriter("/asap3/flash/gpfs/bl1/2017/data/11001733/processed/tof_88_91.h5", chunksize=10)

# This function is called for every single event
# following the given recipe of analysis
def onEvent(evt):
    # Processing rate [Hz]
    analysis.event.printProcessingRate()

    # try:
    #     has_tof = True
    #     evt["DAQ"]["TOF"]
    #     print "We have TOF data!"
    # except RuntimeError:
    #     has_tof = False
    #     #print "No TOF"
    has_tof = False
    
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
                              label='Total ADU', hline=hitScoreThreshold, group='Metric')
    
    plotting.line.plotHistory(evt["analysis"]["litpixel: hitscore"],
                              label='Nr. of lit pixels', hline=hitScoreThreshold, group='Metric')
    analysis.hitfinding.hitrate(evt, hit, history=50)


    if hit and has_tof:
        print evt["DAQ"]["TOF"].data
        print evt["motorPositions"]["InjectorZ"].data
        plotting.line.plotTrace(evt["DAQ"]["TOF"], label='TOF', history=100, tracelen=20000, name="TOF", group="TOF")
        plotting.line.plotHistory(evt["motorPositions"]["InjectorZ"], label="InjectorZ (with TOF)", group="TOF")
        plotting.image.plotImage(evt[detector_type][detector_key], name="pnCCD (Hits with TOF)", group='TOF', mask=mask_center_s)

        D = {}
        D['TOF'] = evt['DAQ']['TOF'].data
        D['pnCCD'] = evt[detector_type][detector_key].data
        D['InjectorZ'] = evt["motorPositions"]["InjectorZ"].data
        
        if do_write:
            W.write_slice(D)



def end_of_run():
    if do_write:
        W.close()
