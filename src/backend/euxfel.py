# --------------------------------------------------------------------------------------
# Copyright 2017, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Online backend for reading EuXFEL events via the Karabo-bridge."""
from __future__ import print_function # Compatibility with python 2 and 3
import os
import numpy
import datetime
from pytz import timezone
from backend.event_translator import EventTranslator
from backend.record import Record, add_record
from backend import Worker
from . import ureg
import logging
import ipc
import karabo_bridge

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
        # CalibSim: This is calibration in simulation mode with (Y,X,nmodules)
        # Raw: This is for reading uncalibrated data online, don't know shape yet
        self._data_format = "Calib"
        if 'EuXFEL/DataFormat' in state:
            self._data_format = state["EuXFEL/DataFormat"]
        if not self._data_format in ["Calib", "Raw"]:
            raise ValueError("You need to set the 'EuXFEL/DataFormat'"
                             " in the configuration as 'Calib' or 'Raw'")
            
        # Switch for receiving full trains (current default) or individual pulses
        self._recv_trains = True
        if 'EuXFEL/RecvFullTrains' in state:
            self._recv_trains = state['EuXFEL/RecvFullTrains']
        self._train_buffer = None
        self._train_meta = None
        self._remaining_pulses = 0

        # Start Karabo client
        self._krb_client = karabo_bridge.Client(dsrc)
        
        # Define how to translate between EuXFEL types and Hummingbird ones
        self._n2c = {}
        self._n2c["SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED"] = ['photonPixelDetectors', 'eventID']
        
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
        self._s2c["SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED"] = "AGIPD"
        ## Add more AGIPD sources here
        
    def next_event(self):
        """Grabs the next event returns the translated version."""
        # when reading full trains, no remaining pulses in the buffer
        if self._recv_trains and not self._remaining_pulses:
            self._train_buffer, self._train_meta = self._krb_client.next()
            self._train_id = self._train_buffer[list(self._train_buffer.keys())[0]]['image.trainId']
            self._train_length = len(self._train_id)
            self._remaining_pulses = self._train_length
            #print("Received train: ", self._train_id)
            #print("Remaining pulses: ", self._remaining_pulses)
        # when reading full trains, still pulses remaining in the buffer
        if self._recv_trains and self._remaining_pulses:
            index = self._train_length - self._remaining_pulses
            evt = {}
            for source, d in self._train_meta.items():
                evt[source] = {}
                for k,v in self._train_buffer[source].items():
                    if type(v) is list:
                        continue
                    # Make sure we are filtering the correct dimension
                    if v.shape[0] != self._train_length:
                        dim = numpy.where(numpy.array(v.shape) == self._train_length)[0][0]
                        evt[source][k] = v.swapaxes(0,dim)[index]
                    else:
                        evt[source][k] = v[index]
                for k,v in d.items():
                    evt[source][k] = v
            self._remaining_pulses = max(0, self._remaining_pulses - 1)
        # when reading individual trains
        if not self._recv_trains:
            evt, metadata = self._krb_client.next()
            for source, d in metadata.items():
                for k,v in d.items():
                    evt[source][k] = v
        return EventTranslator(evt, self)

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
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        return self.translate(evt, 'eventID')['Timestamp'].timestamp
    
    def _tr_photon_detector(self, values, obj, evt_key):
        """Translates pixel detector into Humminbird ADU array"""
        img = obj['image.data']
        # If shortest dimension (modules) is last, swap it with zero dimension
        # This is necesary for the simulated karabo-bridge output, should happen in online mode
        if not (numpy.array(img.shape).argmin() == 0):
            img = img.swapaxes(0,-1)
        # Check that first is either 16 or 1 module
        assert (img.shape[0] == 16 or img.shape[0].shape == 1)
        # Check that module has shape (512,128)
        assert img.shape[1] == 512
        assert img.shape[2] == 128
        # If data is calibrated read the gain and add to stack after last module
        if self._data_format == 'Calib':
            gain = obj['image.gain']
            # This needs to be tested if it also works when we receive only one module
            img = numpy.vstack((img, gain[numpy.newaxis, ...]))
        elif self._data_format == 'Raw':
            pass
        else:
            raise NotImplementedError("DataFormat should be 'Calib' or 'Raw''")
        add_record(values, 'photonPixelDetectors', self._s2c[evt_key], img, ureg.ADU)
        
    def _tr_event_id(self, values, obj):
        """Translates euxfel event ID from some source into a hummingbird one"""
        pulseid = int(obj["image.pulseId"])
        timestamp = int(obj['timestamp.sec']) + int(obj['timestamp.frac']) * 1e-18 + pulseid * 1e-2
        time = datetime.datetime.fromtimestamp(timestamp, tz=timezone('utc'))
        time = time.astimezone(tz=timezone('CET'))
        rec = Record('Timestamp', time, ureg.s)
        rec.pulseId = int(obj['image.pulseId'])
        rec.cellId  = int(obj['image.cellId'])
        rec.trainId = int(obj['image.trainId'])
        rec.timestamp = timestamp
        values[rec.name] = rec

        
