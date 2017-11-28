# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import print_function, absolute_import # Compatibility with python 2 and 3
import numpy as np
from backend import ureg
from backend import add_record
import h5py

def get_panel(evt, record, index):
    """
    Returns one out of the 16 individual panels of the AGIPD by indexing the raw (16,512,128) array.
    """
    return add_record(evt['analysis'], 'analysis', 'AGIPD_panel_%d' %(index), record.data[index])

# A few constants...
nGains = 3
nCells = 30

class AGIPD_Calibrator:

    def __init__(self, filename):
        self._read_calibration_data(filename)    

    def _read_calibration_data(self, filename):
        # Anton's AGIPD calibration format
        #> h5ls calib/agipd/Cheetah-AGIPD00-calib.h5
        #AnalogOffset             Dataset {3, 32, 512, 128} H5T_STD_I16LE
        #Badpixel                 Dataset {3, 32, 512, 128} H5T_STD_U8LE
        #DigitalGainLevel         Dataset {3, 32, 512, 128} H5T_STD_U16LE
        #RelativeGain             Dataset {3, 32, 512, 128} H5T_IEEE_F32LE
        with h5py.File(filename) as f:
            self._badpixData       = np.asarray(f["/Badpixel"])
            self._offsetData       = np.asarray(f["/AnalogOffset"])
            self._relativeGainData = np.asarray(f["/RelativeGain"])
            self._gainLevelData    = np.asarray(f["/DigitalGainLevel"])
                
    def calibrate(self, aduData, gainData, cellID, apply_gain_switch=False):
        assert aduData is not None
        assert gainData is not None
        assert 0 <= cellID < nCells

        calData = np.copy(aduData)
        
        cellDarkOffeset  = np.asarray([self._darkOffsetData[g][cellID] for g in range(nGains)])
        cellGainLevel    = np.asarray([self._gainLevelData[g][cellID] for g in range(nGains)])
        cellRelativeGain = np.asarray([self._relativeGainData[g][cellID] for g in range(nGains)])
        cellBadpix       = np.asarray([self._badpixData[g][cellID] for g in range(nGains)])

        badpixMask = cellBadpix != 0
        
        if apply_gain_switch:
            # Option: bypass multi-gain calibration
            # In this case use only the gain0 offset
            calData -= cellDarkOffset
	else:
	    # Determine which gain stage by thresholding
            # Thresholding for gain level 3 is dodgy - thresholds merge
            # Ignore gain level 3 for now and work on levels 0,1
            pixGainLevel0 = gainData < cellGainLevel[1]
            pixGainLevel1 = pixGainLevel0 == False
            pixGainLevel2 = np.zeros(shape=aduData.shape, dtype='bool')

            pixGainLevels = [pixGainLevel0, pixGainLevel1, pixGainLevel2]
            
            # Subtract the appropriate offset
            for lvl, pixGain in enumerate(pixGainLevels):
                if not pixGain.any():
                    continue
	        calData[pixGain] -= cellDarkOffset[pixGain]
		calData[pixGain] *= cellRelativeGain[pixGain]

        return calData, badpixMask

