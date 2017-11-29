# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import print_function, absolute_import # Compatibility with python 2 and 3
import numpy as np
from backend import ureg
from backend import add_record
import h5py

import analysis.cfel_geom

_agipd_calibrator = None
def init_calib(filename):
    global _agipd_calibrator
    _agipd_calibrator = AGIPD_Calibrator(filename)

_agipd_x = None
_agipd_y = None
_agipd_r = None
def init_geom(filename):
    global _agipd_x
    global _agipd_y
    _agipd_x, _agipd_y, _agipd_r = analysis.cfel_geom.pixel_maps_from_geometry_file(filename)
    
def getAGIPDCell(evt, record, cellID, calibrate=True, copy=True):
    """
    Returns one out of the 16 individual panels of the AGIPD by indexing the raw (16,512,128) array.

    For obtaining calibrated data set calibrate=True and make sure the calibration data is initialised 
    by calling init_agipd(filename=path_to_calibration_file) before.
    """

    aduData  = record.data[0][cellID]
    gainData = record.data[1][cellID]

    if calibrate:
        calData, badpixMask = _agipd_calibrator.calibrate_cell(aduData=aduData, gainData=gainData, cellID=cellID, copy=copy)
        return add_record(evt['analysis'], 'analysis', 'AGIPD_panel_%d_cal' %(index), calData)
    else:
        return add_record(evt['analysis'], 'analysis', 'AGIPD_panel_%d_raw' %(index), aduData)
    

def getAGIPD(evt, record, calibrate=True, assemble=False, copy=True):
    """
    Returns entire AGIPD panel array of shape (16,512,128).

    For obtaining calibrated data set calibrate=True and make sure the calibration data is initialised 
    by calling init_calib(filename=location_of_calibration_file) before.

    For obtaining assembled data set assemble=True and make sure the geometry data is initalised by
    calling init_geom(filename=location_of_calibration_file) before.

    """

    aduData  = record.data[0]
    gainData = record.data[1]
    
    calData, badpixMask = _agipd_calibrator.calibrate_all_cells(aduData=aduData, gainData=gainData, copy=copy)

    if assemble:
        img = analysis.cfel_geom.apply_geometry_from_pixel_maps(data_as_slab, yx, im_out=None)
        return add_record(evt['analysis'], 'analysis', 'AGIPD_assembled' %(index), img)
    else:
        return add_record(evt['analysis'], 'analysis', 'AGIPD', calData)


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

    def calibrate_all_cells(self, aduData, gainData, apply_gain_switch=False, copy=True):
        badpixMask = np.empty(shape=(32, 512, 128), dtype='bool')
        if copy:
            calData = np.copy(aduData)
        else:
            calData = aduData
        for cellID in range(nCells):
            self.calibrate_cell(aduData=calData[cellID],
                                gainData=gainData[cellID],
                                cellID=cellID, apply_gain_switch=apply_gain_switch, copy=copy, mask_write_to=badpixMask[cellID])
                
        return calData, badpixMask

    def calibrate_cell(self, aduData, gainData, cellID, apply_gain_switch=False, copy=True, mask_write_to=None):
        assert aduData is not None
        assert gainData is not None
        assert 0 <= cellID < nCells

        # WARNING: we are overwriting the input data for performance reasons
        copy_data = False
        if copy_data:
            calData = np.copy(aduData)
        else:
            calData = aduData
        
        cellDarkOffeset  = np.asarray([self._darkOffsetData[g][cellID] for g in range(nGains)])
        cellGainLevel    = np.asarray([self._gainLevelData[g][cellID] for g in range(nGains)])
        cellRelativeGain = np.asarray([self._relativeGainData[g][cellID] for g in range(nGains)])
        cellBadpix       = np.asarray([self._badpixData[g][cellID] for g in range(nGains)])

        if mask_write_to is not None:
            baspixMask = mask_write_to
        else:
            np.empty(shape=aduData.shape, dtype='bool')
        badpixMask[:] = (cellBadpix != 0)[:]
        
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


