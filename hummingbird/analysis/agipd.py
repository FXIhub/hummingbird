# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import h5py
import numpy as np

from hummingbird.backend import add_record, ureg
from . import cfel_geom

_nGains = 3
_nPanels = 16
_nCells = 64

_agipd_calibrator = None
def init_calib(filenames):
    global _agipd_calibrator
    _agipd_calibrator = AGIPD_Calibrator(filenames)

_agipd_yx         = None
_agipd_slap_shape = None
_agipd_img_shape  = None
_agipd_rot180     = False
def init_geom(filename, rot180=False):
    global _agipd_yx, _agipd_slap_shape, _agipd_img_shape, _agipd_rot180
    _agipd_yx, _agipd_slap_shape, _agipd_img_shape = analysis.cfel_geom.pixel_maps_for_image_view(geometry_filename=filename)    
    _agipd_yx = np.asarray(_agipd_yx, dtype=np.int64)
    _agipd_yx = _agipd_yx.reshape((2, 16, _agipd_yx[0].size//16))
    _agipd_rot180 = rot180    
    
def getAGIPD(evt, record, cellID=None, panelID=None, calibrate=True, assemble=False, copy=True, crop=None):
    """
    Returns individual panels or the entire frame of the AGIPD.

    For obtaining calibrated data set calibrate=True and make sure the calibration data is initialised 
    by calling init_agipd(filename=path_to_calibration_file) before.

    For obtaining assembled data set assemble=True and make sure the geometry data is initalised by
    calling init_geom(filename=location_of_calibration_file) before.

    """

    nPanels = record.data.shape[1]
    is_group_of_panels = isinstance(panelID, list)
    if is_group_of_panels and not nPanels == len(panelID):
        print("ERROR: Please provide a panelID list that matches the number of panels given.")
        return
    is_isolated_panel = (panelID is not None if not is_group_of_panels else False)
    if panelID is None and nPanels == 1:
        print("ERROR: Please provide a panelID to identify the panel that shall be processed.")
        return

    if is_isolated_panel:
        aduData  = record.data[0][0 if nPanels == 1 else panelID]
        gainData = record.data[1][0 if nPanels == 1 else panelID]
    else:
        aduData  = record.data[0] 
        gainData = record.data[1]
        
    outData = np.array(aduData, copy=copy, dtype='float32')
        
    if is_isolated_panel:
        if calibrate:
            outData, maskData = _agipd_calibrator.calibrate_panel(aduData=aduData, gainData=gainData,
                                                                  panelID=panelID, cellID=cellID, write_to_data=outData)
            add_record(evt['analysis'], 'analysis', 'AGIPD_panel_%d_mask' % panelID, maskData)
            return add_record(evt['analysis'], 'analysis', 'AGIPD_panel_%d_cal' %(panelID), outData)
        else:
            #add_record(evt['analysis'], 'analysis', 'AGIPD_panel_%d_mask' % panelID, maskData)
            return add_record(evt['analysis'], 'analysis', 'AGIPD_panel_%d_raw' %(panelID), outData)
    else:
        if calibrate:
            outData = np.array(aduData, copy=copy, dtype=np.float32)
            _agipd_calibrator.calibrate_panels(aduData=outData, gainData=gainData,
                                               panelID=panelID, cellID=cellID, write_to_data=outData)
        if assemble:
            img = np.zeros(shape=_agipd_img_shape, dtype=outData.dtype)
            if panelID is None:
                p_list = range(_nPanels)
            else:
                p_list = panelID
            for i, p in enumerate(p_list):
                img[_agipd_yx[0][p], _agipd_yx[1][p]] = outData[i].ravel()
            if crop is not None:
                img = img[crop[0][0]:crop[0][1], crop[1][0]:crop[1][1]]
            if _agipd_rot180:
                img = img[::-1, ::-1]
            return add_record(evt['analysis'], 'analysis', 'AGIPD_assembled', img)
        else:
            return add_record(evt['analysis'], 'analysis', 'AGIPD', outData)

class AGIPD_Calibrator:

    def __init__(self, filenames):
        assert len(filenames) == _nPanels
        self._nCells = None
        self._badpixData       = []
        self._darkOffsetData   = []
        self._relativeGainData = []
        self._gainLevelData    = []
        for filename in sorted(filenames):
            self._read_and_append_calibration_data(filename=filename)
        self._badpixData       = np.asarray(self._badpixData)
        self._darkOffsetData   = np.asarray(self._darkOffsetData)
        self._relativeGainData = np.asarray(self._relativeGainData)
        self._gainLevelData    = np.asarray(self._gainLevelData)

    def _read_and_append_calibration_data(self, filename):
        # Meaning of indices: (gainID, cellID, pixcol, pixrow)
        # Anton's AGIPD calibration format
        #> h5ls calib/agipd/Cheetah-AGIPD00-calib.h5
        #AnalogOffset             Dataset {3, 64, 512, 128} H5T_STD_I16LE
        #Badpixel                 Dataset {3, 64, 512, 128} H5T_STD_U8LE
        #DigitalGainLevel         Dataset {3, 64, 512, 128} H5T_STD_U16LE
        #RelativeGain             Dataset {3, 64, 512, 128} H5T_IEEE_F32LE
        with h5py.File(filename) as f:
            self._badpixData.append(np.asarray(f["/Badpixel"]))
            self._darkOffsetData.append(np.asarray(f["/AnalogOffset"]))
            self._relativeGainData.append(np.asarray(f["/RelativeGain"]))
            self._gainLevelData.append(np.asarray(f["/DigitalGainLevel"]))
            assert _nCells == f["/Badpixel"].shape[1]
            assert _nCells == f["/AnalogOffset"].shape[1]
            assert _nCells == f["/RelativeGain"].shape[1]
            assert _nCells == f["/DigitalGainLevel"].shape[1]
            

    def calibrate_panels(self, aduData, gainData, cellID, panelID=None, apply_gain_switch=False, write_to_mask=None, write_to_data=None):

        if panelID is None:
            p_list = range(_nPanels)
        else:
            p_list = panelID
        
        if write_to_data is not None:
            assert str(write_to_data.dtype) == 'float32'
            outData = write_to_data
        else:
            outData = np.array(aduData, copy=True, dtype=np.float32)

        if write_to_mask is not None:
            assert str(write_to_mask.dtype) == 'bool'
            badpixMask = write_to_mask
        else:
            badpixMask = np.ones(shape=aduData.shape, dtype=np.bool)
            
        for i, p in enumerate(p_list):
            self.calibrate_panel(aduData=aduData[i],
                                 gainData=gainData[i],
                                 panelID=p,
                                 cellID=cellID,
                                 apply_gain_switch=apply_gain_switch,
                                 write_to_data=outData[i],
                                 write_to_mask=badpixMask[i])

        return outData, badpixMask

    def calibrate_panel(self, aduData, gainData, cellID, panelID, apply_gain_switch=True, write_to_mask=None, write_to_data=None):
        assert aduData is not None
        assert gainData is not None
        assert (0 <= cellID < _nCells)
        assert (0 <= panelID < _nPanels)

        if write_to_data is not None:
            assert str(write_to_data.dtype) == 'float32'
            outData = write_to_data
        else:
            outData = np.array(aduData, copy=True, dtype=np.float32)

        if write_to_mask is not None:
            assert str(write_to_mask.dtype) == 'bool'
            badpixMask = write_to_mask
        else:
            badpixMask = np.ones(shape=aduData.shape, dtype=np.bool)
            
        offset = 0
        cellBadpix       = np.asarray([self._badpixData[panelID][g][cellID+offset] for g in range(_nGains)])
        cellDarkOffset   = np.asarray([self._darkOffsetData[panelID][g][cellID+offset] for g in range(_nGains)])
        cellRelativeGain = np.asarray([self._relativeGainData[panelID][g][cellID+offset] for g in range(_nGains)])
        cellGainLevel    = np.asarray([self._gainLevelData[panelID][g][cellID+offset] for g in range(_nGains)])
        
        if apply_gain_switch:
            # Option: bypass multi-gain calibration
            # In this case use only the gain0 offset
            outData -= cellDarkOffset[0]
        else:
	    # Determine which gain stage by thresholding
            # Thresholding for gain level 3 is dodgy - thresholds merge
            # Ignore gain level 3 for now and work on levels 0,1
            pixGainLevel0 = gainData < cellGainLevel[1]
            pixGainLevel1 = pixGainLevel0 == False
            # Do not use last gain level
            pixGainLevel2 = np.zeros(shape=aduData.shape, dtype='bool')

            pixGainLevels = [pixGainLevel0, pixGainLevel1, pixGainLevel2]
            
            # Subtract the appropriate offset
            for g, pixGain in enumerate(pixGainLevels):
                if not pixGain.any():
                    continue
                outData[pixGain] = (outData[pixGain] - cellDarkOffset[g][pixGain]) * cellRelativeGain[g][pixGain]
                outData[pixGain] *= (cellBadpix[g][pixGain] == 0)
                badpixMask[pixGain] = (cellBadpix[g][pixGain] == 0)

        return outData, badpixMask
