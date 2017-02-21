# Import analysis/plotting modules
import analysis.event
import analysis.hitfinding
import plotting.image
import plotting.line
import plotting.correlation
import plotting.histogram
from backend.record import add_record
import numpy as np
import time
import ipc

# Quick config parameters
hitScoreThreshold = 9000
aduThreshold = 200

# Specify the facility
state = {}
state['Facility'] = 'FLASH'
# Specify folders with frms6 and darkcal data
state['FLASH/DataGlob'] = '/asap3/flash/gpfs/bl1/2017/data/11001733/raw/pnccd/data/*.frms6'
state['FLASH/CalibGlob'] = '/asap3/flash/gpfs/bl1/2017/data/11001733/raw/pnccd/calib'
state['FLASH/DAQFolder'] = '/asap3/flash/gpfs/bl1/2017/data/11001733/raw/pnccd/daq'
state['FLASH/MotorFolder'] = '/home/ekeberg/Beamtimes/Holography2017/motor_positions/motor_foo.data'
#state['FLASH/DataGlob'] = '/var/acqu/bl1camp/Chapman_2016/CCD_Data/Databg_20160518_0622*.frms6'
#state['FLASH/CalibGlob'] = '/var/acqu/bl1camp/Chapman_2016/CCD_Calib/*.darkcal.h5'
#state['FLASH/MotorFolder'] = 'motors/stage-server/'
#state['FLASH/DAQFolder'] = '/var/acqu/bl1camp/Chapman_2016/DAQ/'
state['do_offline'] = True
#state['FLASH/ProcessingRate'] = 1

def calculate_epoch_times(evt, time_sec, time_usec):
    add_record(evt['ID'], 'ID', 'time', time_sec.data + 1.e-6*time_usec.data)
    #add_record(evt['ID'], 'ID', 'timeAgo', time.time() - (time_sec.data + 1.e-6*time_usec.data))
    # Calculating timeAgo with 606 second offset due to miscalibration of pnCCD server clock
    add_record(evt['ID'], 'ID', 'timeAgo', -606. + time.time() - (time_sec.data + 1.e-6*time_usec.data))

# This function is called for every single event
# following the given recipe of analysis
def onEvent(evt):
    # Processing rate [Hz]
    analysis.event.printProcessingRate()

    # Calculate time and add to PlotHistory
    # calculate_epoch_times(evt, evt["ID"]["tv_sec"], evt["ID"]["tv_usec"])
    # plotting.line.plotHistory(evt['ID']['timeAgo'], label='Event Time (s)', group='ID')
    # plotting.line.plotHistory(evt['ID']['tv_sec'], label='Epoch Time (s)', group='ID')

    # Do basic hitfinding using lit pixels
    analysis.hitfinding.countLitPixels(evt, evt["photonPixelDetectors"]["pnCCD"], 
                                       aduThreshold=aduThreshold, 
                                       hitscoreThreshold=hitScoreThreshold)

    hit = evt["analysis"]["litpixel: isHit"].data
    plotting.line.plotHistory(evt["analysis"]["litpixel: hitscore"],
                              label='Nr. of lit pixels', hline=100, group='Metric')
    analysis.hitfinding.hitrate(evt, hit, history=5000)

    plotting.histogram.plotHistogram(evt["analysis"]["litpixel: hitscore"],
                                     hmin=30000, hmax=45000, bins=50,
                                     name="Lit Pixel Histogram", group="Histograms")
    plotting.image.plotImage(evt['photonPixelDetectors']['pnCCD'], name="pnCCD (All)", group='Images')

    if ipc.mpi.is_main_worker():
        plotting.line.plotHistory(evt["analysis"]["hitrate"], label='Hit rate [%]', group='Metric')
        # plotting.correlation.plotMeanMap(evt['motorPositions']['nozzle_x'], evt['motorPositions']['nozzle_y'],
        #                              #evt['analysis']['litpixel: hitscore'].data / 1e5, 
        #                              evt['analysis']['hitrate'].data, 
        #                              xmin=0.68, xmax=0.72, ymin=4.20, ymax=4.23,
        #                              name='Hitscore mean map vs nozzle_xy',
        #                              xlabel='nozzle_x (mm)', 
        #                              ylabel='nozzle_y (mm)',
        #                              group='Metric')
    if hit:
        pass
        # Visualize detector image if hit
        plotting.image.plotImage(evt['photonPixelDetectors']['pnCCD'], name="pnCCD (Hits)", group='Images')
    
    # Scatter plot
    # plotting.correlation.plotScatter(evt['ID']['time'], evt['analysis']['litpixel: hitscore'], 
    #                                  name='Hit Score vs t', 
    #                                  xlabel='Epoch Time (s)', 
    #                                  ylabel='Hit Score',
    #                                  group='Metric')
    # plotting.correlation.plotScatter(evt['ID']['time'], evt['ID']['timeAgo'], 
    #                                  name='Delay vs time', 
    #                                  xlabel='Epoch Time (s)', 
    #                                  ylabel='Delay (s)',
    #                                  group='Metric')
    # plotting.correlation.plotScatter(evt['motorPositions']['nozzle_x'], evt['analysis']['litpixel: hitscore'], 
    #                                  name='Hitscore vs nozzle_x', 
    #                                  xlabel='nozzle_x (mm)', 
    #                                  ylabel='Hit Score',
    #                                  group='Metric')
    # plotting.correlation.plotScatter(evt['motorPositions']['nozzle_y'], evt['analysis']['litpixel: hitscore'], 
    #                                  name='Hitscore vs nozzle_y', 
    #                                  xlabel='nozzle_y (mm)', 
    #                                  ylabel='Hit Score',
    #                                  group='Metric')

    # plotting.line.plotHistory(evt["ID"]["bunch_sec"], label="Bunch sec")
