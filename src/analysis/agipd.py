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

_nGains = 3
_nPanels = 16
_nCells = 30

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
    _agipd_rot180 = rot180

def getAGIPD(evt, record, cellID=None, panelID=None, calibrate=True, assemble=False, copy=True):
    """
    Returns individual panels or the entire frame of the AGIPD.

    For obtaining calibrated data set calibrate=True and make sure the calibration data is initialised 
    by calling init_agipd(filename=path_to_calibration_file) before.

    For obtaining assembled data set assemble=True and make sure the geometry data is initalised by
    calling init_geom(filename=location_of_calibration_file) before.

    """

    is_isolated_panel = record.data.shape[1] == 1
    if panelID is None and is_isolated_panel:
        print("ERROR: Please provide a panelID to identify the panel that shall be processed.")
        return
    
    if is_isolated_panel:
        aduData  = record.data[0][0 if is_isolated_panel else panelID]
        gainData = record.data[1][0 if is_isolated_panel else panelID]
        calData = np.array(aduData, copy=copy, dtype=np.int32)
        if calibrate:
            _agipd_calibrator.calibrate_panel(aduData=calData, gainData=gainData,
                                              panelID=panelID, cellID=cellID)
            return add_record(evt['analysis'], 'analysis', 'AGIPD_panel_%d_cal' %(panelID), calData)
        else:
            return add_record(evt['analysis'], 'analysis', 'AGIPD_panel_%d_raw' %(panelID), aduData)
    else:
        aduData  = record.data[0] 
        gainData = record.data[1]
        calData = np.array(aduData, copy=copy, dtype=np.int32)
        if calibrate:
            _agipd_calibrator.calibrate_all_panels(aduData=calData, gainData=gainData, cellID=cellID)
        if assemble:
            img = np.zeros(shape=_agipd_img_shape, dtype=calData.dtype)
            img[_agipd_yx[0], _agipd_yx[1]] = calData.ravel()
            if _agipd_rot180:
                img = img[::-1, ::-1]
            return add_record(evt['analysis'], 'analysis', 'AGIPD_assembled', img)
        else:
            return add_record(evt['analysis'], 'analysis', 'AGIPD', calData)


class AGIPD_Calibrator:

    def __init__(self, filenames):
        assert len(filenames) == _nPanels
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
        #AnalogOffset             Dataset {3, 32, 512, 128} H5T_STD_I16LE
        #Badpixel                 Dataset {3, 32, 512, 128} H5T_STD_U8LE
        #DigitalGainLevel         Dataset {3, 32, 512, 128} H5T_STD_U16LE
        #RelativeGain             Dataset {3, 32, 512, 128} H5T_IEEE_F32LE
        with h5py.File(filename) as f:
            self._badpixData.append(np.asarray(f["/Badpixel"]))
            self._darkOffsetData.append(np.asarray(f["/AnalogOffset"]))
            self._relativeGainData.append(np.asarray(f["/RelativeGain"]))
            self._gainLevelData.append(np.asarray(f["/DigitalGainLevel"]))

    def calibrate_all_panels(self, aduData, gainData, cellID, apply_gain_switch=False):
        # WARNING: aduData is overwritten!
        badpixMask = np.empty(shape=(32, 512, 128), dtype='bool')

        for panelID in range(_nPanels):
            self.calibrate_panel(aduData=aduData[panelID],
                                 gainData=gainData[panelID],
                                 panelID=panelID,
                                 cellID=cellID,
                                 apply_gain_switch=apply_gain_switch, mask_write_to=badpixMask[panelID])

    def calibrate_panel(self, aduData, gainData, cellID, panelID, apply_gain_switch=False, mask_write_to=None):
        # WARNING: aduData is overwritten!
        apply_gain_switch = True
        assert aduData is not None
        assert gainData is not None
        assert (0 <= cellID < _nCells)
        assert (0 <= panelID < _nPanels)
        assert str(aduData.dtype) == 'int32'
            
        cellBadpix       = np.asarray([self._badpixData[panelID][g][cellID] for g in range(_nGains)])
        cellDarkOffset   = np.asarray([self._darkOffsetData[panelID][g][cellID] for g in range(_nGains)])
        cellRelativeGain = np.asarray([self._relativeGainData[panelID][g][cellID] for g in range(_nGains)])
        cellGainLevel    = np.asarray([self._gainLevelData[panelID][g][cellID] for g in range(_nGains)])

        if mask_write_to is not None:
            badpixMask = mask_write_to
        else:
            badpixMask = np.empty(shape=aduData.shape, dtype='bool')
        
        if apply_gain_switch:
            # Option: bypass multi-gain calibration
            # In this case use only the gain0 offset
            aduData -= cellDarkOffset[0]
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
                aduData[pixGain] = aduData[pixGain] - cellDarkOffset[g][pixGain]
                aduData[pixGain] = aduData[pixGain] * cellRelativeGain[g][pixGain]
                badpixMask[pixGain] = (cellBadpix[g][pixGain] != 0)

