# Import analysis/plotting modules
import analysis.event
import analysis.hitfinding
import plotting.image
import plotting.line
from backend.record import add_record
import numpy as np
import time

# Quick config parameters
hitScoreThreshold = 155000

# Specify the facility
state = {}
state['Facility'] = 'FLASH'
# Specify folders with frms6 and darkcal data
#state['FLASH/DataFolder'] = '/var/data/Chapman_2016/CCD_Data'
#state['FLASH/CalibFolder'] = '/var/data/Chapman_2016/CCD_Calib'
state['FLASH/DataFolder'] = '/tmp'
state['FLASH/CalibFolder'] = '/tmp'

# This function is called for every single event
# following the given recipy of analysis
def onEvent(evt):

    # Processin rate [Hz]
    analysis.event.printProcessingRate()

    # Calculate time and add to PlotHistory
    add_record(evt['ID'], 'ID', 'Time_ago', time.time() - (evt['ID']['tv_sec'].data + 1.e-6*evt['ID']['tv_usec'].data))
    plotting.line.plotHistory(evt['ID']['Time_ago'], label='Event Time (s)')
    plotting.line.plotHistory(evt['ID']['tv_sec'], label='Epoch Time (s)')

    # Do basic hitfinding using lit pixels
    analysis.hitfinding.countLitPixels(evt, evt["photonPixelDetectors"]["pnCCD"], aduThreshold=200, hitscoreThreshold=hitScoreThreshold)
    hit = evt["analysis"]["litpixel: isHit"].data
    analysis.hitfinding.hitrate(evt, hit, history=5000)
    plotting.line.plotHistory(evt["analysis"]["litpixel: hitscore"], label='Nr. of lit pixels', hline=100)
    plotting.line.plotHistory(evt["analysis"]["hitrate"], label='Hit rate [%]')
    if hit:
        # Visualize detector image if hit
        plotting.image.plotImage(evt['photonPixelDetectors']['pnCCD'])
    
