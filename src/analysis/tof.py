# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
import numpy as np
from backend import ureg
from backend import add_record

def tofPreproc(evt, type, key, outkey=None):
    """ToF baseline correction and inversion
    
    Args:
      :evt:                     The event variable
      :type(str):               The event type
      :key(str):                The event key

    Kwargs:
      :outkey(str):             The event key for the corrected image, default is "corrected - " + key
    
    :Authors:
    """
 
    if outkey is None:
        outkey = "corrected - " + key
    tof_trace = evt[type][key].data

    tof_trace_inverted = tof_trace * -1
        #Find photon peak
        tof_peak_threshold = np.std(tof_trace_inverted[:pre_pp_index])*5

        all_peak_x = np.where(tof_trace_inverted>(np.median(tof_trace_inverted[:pre_pp_index])+tof_peak_threshold))[0]
        any_peaks = all_peak_x.size >= 2
        if any_peaks:
            print all_peak_x 
            diff_x = all_peak_x[1:] - all_peak_x[:-1]
            end_peak = all_peak_x[np.where(diff_x > 1)[0]]
            photon_peak_end = end_peak[0] + 1
            photon_peak_start = all_peak_x[0]
            
    	    #Inverted and baseline corrected Tof signal
            base_line = np.median(tof_trace_inverted[:photon_peak_start])
            
            base_std = np.std(tof_trace_inverted[:photon_peak_start])
    	
            corrected_tof = (tof_trace_inverted-base_line)[photon_peak_end:]
            add_record(evt['analysis'], 'analysis', 'Corrected ToF (base line)', corrected_tof)
            
    	    #Convert to M/Q
            Hpeak = np.argmax(corrected_tof[:hpeak_region])
            new_x = (np.arange(len(corrected_tof)) / float(Hpeak))**2.  
            add_record(evt['analysis'], 'analysis', 'M/Q', new_x)
    	

def tofPeakFinder(

    	    #Integrate peaks
            Hpeak_sum = np.sum(corrected_tof[np.where((new_x >= H_peak_position-H_peak_width) & (new_x <= H_peak_position+H_peak_width))])
            Dpeak_sum = np.sum(corrected_tof[np.where((new_x >= D_peak_position-D_peak_width) & (new_x <= D_peak_position+D_peak_width))])
            Cpeak_sum = np.sum(corrected_tof[np.where((new_x >= C_peak_position-C_peak_width) & (new_x <= C_peak_position+C_peak_width))])
            Opeak_sum = np.sum(corrected_tof[np.where((new_x >= O_peak_position-O_peak_width) & (new_x <= O_peak_position+O_peak_width))])
