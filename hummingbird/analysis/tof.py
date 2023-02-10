# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import numpy as np

from hummingbird.backend import add_record, ureg


def ToFCalib(evt, type, key, photon_peak, Calib_peak, Calib_mass, Calib_q, outkey):
    
    """ToF Calibration, photon peak vs any peak. Array must sart at t0!
    
    Args:
      :evt:                       The event variable
      :type(str):                 The event type
      :key(str):                  The event key
      :photon_peak                Photon peak position (time)
      :Calib_peak                 Calibration peak position (time)
      :Calib_mass                 Calibration ion mass
      :Calib_q                    Calibration ion charge
      :outkey(str):               The event key = 'ToF - M/Q ' + outkey for the new calibrated x-axis, 
    
    :Authors:
      Ida Lundholm (ida.lundholm@icm.uu.se)
    """
    corrected_tof=evt[type][key].data
    new_x = (np.arange(len(corrected_tof)) / float((Calib_peak-photon_peak)/np.sqrt(Calib_mass/Calib_mass)))**2.
    add_record(evt['analysis'], 'analysis', 'ToF - M/Q '+outkey, new_x)

def tofPreproc(evt, type, key, baseline_region_guess, number_of_std=5, photon_peak_position=None, H_position=None, outkey=None):
    """ToF baseline correction and inversion
    
    Args:
      :evt:                       The event variable
      :type(str):                 The event type
      :key(str):                  The event key
      :baseline_region_guess(int) Initial guess for the pre photon peak region used for base line calculation
      :auto_Photon                Find photon peak automatically
      :auto_H                     Find hydrogen peak automatically
      :number_of_std              Number of standard deviations above the median for b 

    Kwargs:
      :outkey(str):             The event key for the corrected image, default is "baseline corrected - " + key
    
    :Authors:
      Ida Lundholm (ida.lundholm@icm.uu.se)
    """
 
    if outkey is None:
        outkey = "Corrected ToF (base line)"
    tof_trace = evt[type][key].data

    tof_trace_inverted = tof_trace * -1
    #Find photon peak
    tof_peak_threshold = np.std(tof_trace_inverted[:baseline_region_guess])*number_of_std
    all_peak_x = np.where(tof_trace_inverted>(np.median(tof_trace_inverted[:baseline_region_guess])+tof_peak_threshold))[0]
    if all_peak_x.size>1:
        diff_x = all_peak_x[1:] - all_peak_x[:-1]
        end_peak = all_peak_x[np.where(diff_x > 1)]
    else:
        add_record(evt['analysis'], 'analysis', outkey, tof_trace_inverted-(np.median(tof_trace_inverted[:baseline_region_guess])+tof_peak_threshold))
        add_record(evt['analysis'], 'analysis', 'ToF - M/Q', np.arange(tof_trace_inverted.shape[0]))
        return

    if photon_peak_position is None:
        if all_peak_x.size >= 1:
            photon_peak_start = all_peak_x[0]
        elif all_peak_x.size == 1:
            photon_peak_end=photon_peak_start+1
        if diff_x[0]>1:
            photon_peak_end=photon_peak_start+1
        else:
            if end_peak.shape>0:
                photon_peak_end = end_peak[0] + 1
            else:
                photon_peak_end = photon_peak_start

    if photon_peak_position is not None:
        photon_peak_end=photon_peak_position
        photon_peak_start=photon_peak_position
    #Inverted and baseline corrected Tof signal
    base_line = np.median(tof_trace_inverted[:photon_peak_start])
    base_std = np.std(tof_trace_inverted[:photon_peak_start])
    
    corrected_tof = (tof_trace_inverted-base_line)[photon_peak_end:]
    add_record(evt['analysis'], 'analysis', outkey, corrected_tof)
    
    if H_position is None:
        if (np.sum(diff_x)!=len(diff_x)):
            #Convert to M/Q
            if end_peak.size>1:
                Hpeak_end=end_peak[1]
            else:
                Hpeak_end=len(corrected_tof)
        Hpeak = np.argmax(corrected_tof[:Hpeak_end])
        new_x = (np.arange(len(corrected_tof)) / float(Hpeak))**2.
        add_record(evt['analysis'], 'analysis', 'ToF - M/Q', new_x)
        
    else:
        new_x = (np.arange(len(corrected_tof)) / float(H_position-photon_peak_end))**2.  
        add_record(evt['analysis'], 'analysis', 'ToF - M/Q', new_x)

def ToFPeakAnalysis(evt, type, key, X0, X1, outkey=None):
    """ToF peak integration and position finder
    
    Args:
      :evt:                       The event variable
      :type(str):                 The event type
      :key(str):                  The event key
      :X0:                        Peak start in M/Q
      :X1:                        Peak end in M/Q
      :outkey(str):               The event key for the peak, default is str(peak position)
    
    :Authors:
      Ida Lundholm (ida.lundholm@icm.uu.se)
    """
    if outkey==None:
        outkey=str(Peak_pos)

    ToF_trace = evt[type][key].data
    MQ=evt['analysis']['ToF - M/Q'].data

    Peak_index  = np.where((MQ >= X0) & (MQ <= X1))[0]
    Peak        = ToF_trace[Peak_index]
    Peak_sum    = np.sum(Peak)
    Peak_pos    = np.argmax(Peak)+Peak_index[0] #Peak position as index
    Peak_pos_MQ = MQ[Peak_pos]
    
    add_record(evt['analysis'], 'analysis', 'ToF Peak ' + outkey, Peak_pos)
    add_record(evt['analysis'], 'analysis', 'ToF Peak Position MQ ' + outkey, Peak_pos_MQ)
    add_record(evt['analysis'], 'analysis', 'ToF Peak Area ' + outkey, Peak_sum)
