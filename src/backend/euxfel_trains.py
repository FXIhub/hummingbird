# --------------------------------------------------------------------------------------
# Copyright 2017, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Train-based online backend for reading EuXFEL events via the Karabo-bridge."""
from __future__ import print_function # Compatibility with python 2 and 3
import os
import numpy
import datetime, time
from pytz import timezone
from backend.event_translator import EventTranslator
from backend.record import Record, add_record
from backend import Worker
from . import ureg
import logging
import ipc
import karabo_bridge
import numpy

from hummingbird import parse_cmdline_args
_argparser = None
def add_cmdline_args():
    global _argparser
    from utils.cmdline_args import argparser
    _argparser = argparser
    ## ADD EuXFEL specific parser arguments here ##


class EUxfelTranslator(object):
    """Translate between EUxfel events and Hummingbird ones"""
    def __init__(self, state):
        self.timestamps = None
        self.library = 'karabo_bridge'

        # parse additional arguments
        cmdline_args = _argparser.parse_args()

        # Read data source, this currently only allows for a single source, e.g. AGIPD
        if 'EuXFEL/DataSource' in state:
            dsrc = state['EuXFEL/DataSource']
        elif('EuXFEL' in state and 'DataSource' in state['EuXFEL']):
            dsrc = state['EuXFEL']['DataSource']
        else:
            raise ValueError("You need to set the '[EuXFEL][DataSource]'"
                             " in the configuration")

        # We allow different data formats
        # Calib: This is calibrated in online mode with (nmodules,X,Y)
        # Raw: This is for reading uncalibrated data online, don't know shape yet
        self._data_format = "Calib"
        if 'EuXFEL/DataFormat' in state:
            self._data_format = state["EuXFEL/DataFormat"]
        if not self._data_format in ["Calib", "Raw"]:
            raise ValueError("You need to set the 'EuXFEL/DataFormat'"
                             " in the configuration as 'Calib' or 'Raw'")
            
        # Option to select specific AGIPD module
        self._sel_module = None
        if 'EuXFEL/SelModule' in state:
            self._sel_module = state['EuXFEL/SelModule']

        # Option to decide about maximum allowd age of trains
        self._max_train_age = 5 # in units of seconds
        if 'EuXFEL/MaxTrainAge' in state:
            self._max_train_age = state['EuXFEL/MaxTrainAge']

        # Option to set maximum nr. of pulses per train
        max_pulses = -1
        if 'EuXFEL/MaxPulses' in state:
            max_pulses = state['EuXFEL/MaxPulses']
            
        # Hardcoded pulse filter
        max_length = 176

        self._pulse_filter = numpy.ones(max_length, dtype='bool')
        # self._pulse_filter = numpy.zeros(max_length, dtype='bool')
        # self._pulse_filter[1::2] = True

        # self._pulse_filter[max_pulses:] = False # Default: disables last cell
        # self._pulse_filter[0] = False # Disables first cell
        # self._pulse_filter[18::32] = False # Bad cells
        # self._pulse_filter[29::32] = False # Possibly bad cells


        # Start Karabo client
        self._krb_client = karabo_bridge.Client(dsrc)
        
        if 'EuXFEL/DataSource_GMD' in state:
            self._krb_gmd_client = karabo_bridge.Client(state['EuXFEL/DataSource_GMD'])
            self._gmd_cache = None
        else:
            self._krb_gmd_client = None

        # Define how to translate between EuXFEL types and Hummingbird ones
        self._n2c = {}
        if self._sel_module is None:
            self._n2c["SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED"] = ['photonPixelDetectors', 'eventID']
        else:
            self._n2c["SPB_DET_AGIPD1M-1/DET/%dCH0:xtdf"%self._sel_module] = ['photonPixelDetectors', 'eventID']
        
        # Calculate the inverse mapping
        self._c2n = {}
        for k, v in self._n2c.items():
            if type(v) is not list:
                v = [v]
            for v2 in v:
                self._c2n[v2] = self._c2n.get(v2, [])
                self._c2n[v2].append(k)

        # Define how to translate between EuXFEL sources and Hummingbird ones
        self._s2c = {}
        if self._sel_module is None:
            self._s2c["SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED"] = "AGIPD"
        else:
            self._s2c["SPB_DET_AGIPD1M-1/DET/%dCH0:xtdf"%self._sel_module] = "AGIPD"
        
        self._s2c["SA3_XTD10_XGM/XGM/DOOCS:output"] = "SASE3 GMD"
        ## Add more AGIPD sources here

    def next_train(self):
        """Asks for next train until its age is within a given time window."""
        buf, meta = self._krb_client.next()

        if(self._krb_gmd_client is not None):    
            if(self._gmd_cache is None or numpy.random.random() < 0.05):            
                gmd_buf, gmd_meta = self._krb_gmd_client.next()
                # Inject the GMD data in the dictionary
                self._gmd_cache = (gmd_buf['SA3_XTD10_XGM/XGM/DOOCS:output'],  gmd_meta['SA3_XTD10_XGM/XGM/DOOCS:output'])
            buf['SA3_XTD10_XGM/XGM/DOOCS:output'] = self._gmd_cache[0]
            meta['SA3_XTD10_XGM/XGM/DOOCS:output'] = self._gmd_cache[1]


        age = numpy.floor(time.time()) - int(meta[list(meta.keys())[0]]['timestamp.sec'])
        if age < self._max_train_age:
            return buf, meta
        else:
            return self.next_train()
        
    def next_event(self):
        """Grabs the next train event returns the translated version."""
        # Populates event dictionary with trains from Karabo Bridge
        train, metadata = self.next_train()
        for source, d in metadata.items():
            for k,v in d.items():
                train[source][k] = v
        return EventTranslator(train, self)

    def event_keys(self, evt):
        """Returns the translated keys available"""
        native_keys = evt.keys()
        common_keys = set()
        for k in native_keys:
            for c in self._native_to_common(k):
                common_keys.add(c)
        # analysis is for values added later on
        return list(common_keys)+['analysis']

    def _native_to_common(self, key):
        """Translates a native key to a hummingbird one"""
        if(key in self._n2c):
            val = self._n2c[key]
            if type(val) is not list:
                val = [val]
            return val
        else:
            return []

    def event_native_keys(self, evt):
        """Returns the native keys available"""
        return evt.keys()

    def translate(self, evt, key):
        """Returns a dict of Records that match a given hummingbird key"""
        values = {}
        if(key in self._c2n):
            return self.translate_core(evt, key)
        elif(key == 'analysis'):
            return {}
        elif(key == 'stream'):
            return {}
        else:
            # check if the key matches any of the existing keys in the event
            event_keys = evt.keys()
            values = {}
            found = False

            if key in event_keys: 
                obj = evt[key]
                for subkey in obj.keys():
                    add_record(values, 'native', '%s[%s]' % (self._s2c[key], subkey),
                               obj[subkey], ureg.ADU)
                return values
            else:
                print('%s not found in event' % (key))

    def translate_core(self, evt, key):
        """Returns a dict of Records that matchs a core Hummingbird key."""
        values = {}
        for k in self._c2n[key]:
            if k in evt:
                if key == 'eventID':
                    self._tr_event_id(values, evt[k])
                elif key == 'photonPixelDetectors':
                    self._tr_photon_detector(values, evt[k], k)
                else:
                    raise RuntimeError('%s not yet supported with key %s' % (k, key))
        return values

    def event_id(self, evt):
        """Returns the first id of a train."""
        return self.translate(evt, 'eventID')['Timestamp'].timestamp[0]

    def train_id(self, evt):
        """Returns the full stack of all event ids within a train."""
        return self.translate(evt, 'eventID')['Timestamp'].timestamp
    
    def _tr_photon_detector(self, values, obj, evt_key):
        """Translates pixel detector into Humminbird ADU array"""
        train_length = numpy.array(obj["image.pulseId"]).shape[-1]
        img = obj['image.data'][..., self._pulse_filter[:train_length]]
        length = len(obj['image.pulseId'][..., self._pulse_filter[:train_length]])
        # Make sure that the pulses are along the zero dimension
        if img.shape[0] != length:
            dim = numpy.where(numpy.array(img.shape) == length)[0][0]
            img = img.swapaxes(0,dim)
        if self._sel_module is not None:
            img = img[numpy.newaxis]
        assert img.ndim == 4
        # If shortest dimension (modules) is last, swap it with second dimension
        # This is necesary for the simulated karabo-bridge output, should not happen in online mode
        if not (numpy.array(img.shape).argmin() == 1):
            img = img.swapaxes(1,-1)
        '''
        # Check that second is either 16 or 1 module
        assert (img.shape[1] == 16 or img.shape[1] == 1)
        # Check that module has shape (512,128)
        assert img.shape[2] == 512
        assert img.shape[3] == 128
        '''
        # If data is calibrated read the gain and add to stack after last module
        if self._data_format == 'Calib':
            gain = obj['image.gain'][..., self._pulse_filter[:train_length]]
            # Make sure that the pulses are along the zero dimension
            if gain.shape[0] != length:
                dim  = numpy.where(numpy.array(gain.shape) == length)[0][0]
                gain = gain.swapaxes(0,dim)
            # This needs to be tested if it also works when we receive only one module
            img = numpy.concatenate((img, gain[:,numpy.newaxis, ...]), axis=1)
        elif self._data_format == 'Raw':
            gain = obj['image.gain'][..., self._pulse_filter[:train_length]]
            if self._sel_module is not None:
                gain = gain[numpy.newaxis]
            # print(img.shape, gain.shape)
            img = numpy.concatenate((img, gain), axis=0)
        else:
            raise NotImplementedError("DataFormat should be 'Calib' or 'Raw''")
        add_record(values, 'photonPixelDetectors', self._s2c[evt_key], img, ureg.ADU)
        
    def _tr_event_id(self, values, obj):
        """Translates euxfel event ID from some source into a hummingbird one"""
        train_length = numpy.array(obj["image.pulseId"]).shape[-1]
        pulseid  = numpy.array(obj["image.pulseId"][...,self._pulse_filter[:train_length]], dtype='int')
        tsec  = numpy.array(obj['timestamp.sec'], dtype='int') 
        tfrac = numpy.array(obj['timestamp.frac'], dtype='int') * 1e-18 
        timestamp = tsec + tfrac + (pulseid / 760.)
        time = numpy.array([datetime.datetime.fromtimestamp(t, tz=timezone('utc')) for t in timestamp])
        rec = Record('Timestamp', time, ureg.s)
        rec.pulseId = pulseid
        rec.cellId  = numpy.array(obj['image.cellId'][...,self._pulse_filter[:train_length]], dtype='int')
        rec.badCells = numpy.array(obj["image.cellId"][...,~self._pulse_filter[:train_length]], dtype='int')
        rec.trainId = numpy.array(obj['image.trainId'][...,self._pulse_filter[:train_length]], dtype='int')
        rec.timestamp = timestamp
        values[rec.name] = rec

        
