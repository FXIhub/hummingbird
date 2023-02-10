# --------------------------------------------------------------------------------------
# Copyright 2017, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Online backend for reading EuXFEL events via the Karabo-bridge."""
from __future__ import print_function  # Compatibility with python 2 and 3

import datetime
import logging
import os
import time

import karabo_bridge
import numpy
from pytz import timezone

from hummingbird import ipc, parse_cmdline_args
from . import EventTranslator, Record, Worker, add_record, ureg

_argparser = None
def add_cmdline_args():
    global _argparser
    from utils.cmdline_args import argparser
    _argparser = argparser
    ## ADD EuXFEL specific parser arguments here ##

MAX_TRAIN_LENGTH = 352

class EUxfelTranslator(object):
    """Translate between EUxfel events and Hummingbird ones"""
    def __init__(self, state):
        self.timestamps = None
        self.library = 'karabo_bridge'

        # parse additional arguments

        cmdline_args = _argparser.parse_args()

        # Read the main data source, e.g. AGIPD
        dsrc = state.get('EuXFEL/DataSource')
        if dsrc is None:
            dsrc = state.get('EuXFEL', {}).get('DataSource')
        if dsrc is None:
            raise ValueError("You need to set the '[EuXFEL][DataSource]'"
                             " in the configuration")

        # The data format for the data source, either "Calib" or "Raw"
        self._data_format = state.get("EuXFEL/DataFormat", "Calib")
        if not self._data_format in ["Calib", "Raw"]:
            raise ValueError("You need to set the 'EuXFEL/DataFormat'"
                             " in the configuration as 'Calib' or 'Raw'")

        # Option to decide about maximum allowd age of trains
        self._max_train_age = state.get('EuXFEL/MaxTrainAge')  # in units of seconds

        # Option to set the first cell to be selected per train
        first_cell = state.get('EuXFEL/FirstCell', 0)

        # Option to set the last cell to be selected per train
        last_cell = state.get('EuXFEL/LastCell', MAX_TRAIN_LENGTH - 1) + 1

        # Option to specify bad cells
        bad_cells = list(state.get('EuXFEL/BadCells', []))

        # Option to read a slow data source, e.g for GMD, MOTORS, ....
        slsrc = state.get('EuXFEL/SlowSource')

        # Option to provide a list of slow data native keys
        self._slow_keys = state.get('EuXFEL/SlowKeys')
        if self._slow_keys is not None:
            self._slow_keys = list(self._slow_keys)

        # Option to provide update frequency for slow data source
        self._slow_update_rate = int(state.get('EuXFEL/SlowUpdate', 1))

        # Cell filter
        cell_filter = numpy.zeros(MAX_TRAIN_LENGTH, dtype='bool')
        cell_filter[first_cell:last_cell] = True
        cell_filter[bad_cells] = False
        self._use_cells = numpy.flatnonzero(cell_filter)

        # Start Karabo client for data source
        self._data_client = karabo_bridge.Client(dsrc)

        # Start Karabo client for slow data source
        self._slow_cache  = None
        self._slow_last_time = 0
        self._slow_client = None
        if slsrc is not None:
            self._slow_client = karabo_bridge.Client(slsrc)

        # Define how to translate between EuXFEL types and Hummingbird ones
        self._n2c = {}
        self._n2c["SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED"] = ['photonPixelDetectors', 'eventID']
        self._n2c["SPB_DET_AGIPD1M-1/CAL/APPEND_RAW"] = ['photonPixelDetectors', 'eventID']
        for module in range(16):
            self._n2c["SPB_DET_AGIPD1M-1/DET/%dCH0:xtdf" % module] = ['photonPixelDetectors', 'eventID']
            self._n2c["SQS_DET_DSSC1M-1/DET/%dCH0:xtdf" % module] = ['photonPixelDetectors', 'eventID']
            
        self._n2c["SQS_NQS_PNCCD1MP/CAL/PNCCD_FMT-0:output"] = ['photonPixelDetectors', 'eventID']
        self._n2c["SA3_XTD10_XGM/XGM/DOOCS:output"] = ['GMD', 'eventID']

        # MCP
        self._n2c["SQS_DIGITIZER_UTC1/ADC/1:network"] = ["trace"]
        # ["digitizers.channel_1_A.raw.samples"] # Change channel

        # GMD 
        # "data.intensitySa3TD" # SASE3
        # "data.intensitySa1TD" # SASE1

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
        self._s2c["SPB_DET_AGIPD1M-1/CAL/APPEND_RAW"] = "AGIPD"
        self._s2c["SPB_DET_AGIPD1M-1/DET/STACKED:xtdf"] = "AGIPD"

        for module in range(16):
            self._s2c["SPB_DET_AGIPD1M-1/DET/%dCH0:xtdf" % module] = ("AGIPD%02d" % module)
            self._s2c["SQS_DET_DSSC1M-1/DET/%dCH0:xtdf" % module] = ("DSSC%02d" % module)

        self._s2c["SQS_NQS_PNCCD1MP/CAL/PNCCD_FMT-0:output"] = "pnCCD"

        self._s2c["SA3_XTD10_XGM/XGM/DOOCS:output"] = "GMD"
        ## Add more AGIPD sources here

    def append_slow_data(self, buf, meta):
        """Append slow data to train buffer"""
        do_update =  (time.time() - self._slow_last_time) > self._slow_update_rate
        if do_update or self._slow_cache is None:
            self._slow_cache = self._slow_client.next() 
            self._slow_last_time = time.time()
        
        if self._slow_keys is not None:
            for k in self._slow_keys:
                buf[k]  = self._slow_cache[0][k]
                meta[k] = self._slow_cache[1][k]
        else:
            for k,v in self._slow_cache[0].items():
                buf[k] = v
            for k,v in self._slow_cache[1].items():
                meta[k] = v
        return buf, meta

    def next_train(self):
        """Asks for next train until its age is within a given time window."""
        buf, meta = self._data_client.next()
        logging.debug("Received train data")

        if(self._slow_client is not None): 
            buf, meta = self.append_slow_data(buf, meta)
       
        age = time.time()
        age -= meta[list(meta.keys())[0]].get('timestamp', age)
        if self._max_train_age is None or age < self._max_train_age:
            return buf, meta
        else:
            logging.info("Skipping train data with age %f > %f", age, self._max_train_age)
            return self.next_train()

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
                    add_record(values, 'native', '%s' % (subkey),
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
                elif key == 'GMD':
                    self._tr_gmd(values, evt[k], k)
                elif key == "trace":
                    self._tr_trace_sqs_pnccd(values, evt[k], k)
                else:
                    raise RuntimeError('%s not yet supported with key %s' % (k, key))
        return values


class EUxfelTrainTranslator(EUxfelTranslator):
    """Translate between EUxfel train events and Hummingbird ones"""
    def __init__(self, state):
        EUxfelTranslator.__init__(self, state)
          
    def next_event(self):
        """Grabs the next train event returns the translated version."""
        # Populates event dictionary with trains from Karabo Bridge
        train, metadata = self.next_train()
        for source, d in metadata.items():
            for k,v in d.items():
                train[source][k] = v
        return EventTranslator(train, self)
        
    def event_id(self, evt):
        """Returns the first id of a train."""
        return self.translate(evt, 'eventID')['Timestamp'].timestamp[0]

    def train_id(self, evt):
        """Returns the full stack of all event ids within a train."""
        return self.translate(evt, 'eventID')['Timestamp'].timestamp


    def _tr_AGIPD(self, values, obj, evt_key):
        """Translates an AGIPD detector or module into Humminbird ADU array"""
        if('image.pulseId' not in obj or 'image.data' not in obj):
            logging.warning('Could not find an AGIPD data')
            return
        cellid = numpy.squeeze(obj["image.cellId"]).astype(int)
        cells = numpy.in1d(cellid, self._use_cells)
        # When reading from the real live data stream the data looks like
        # (modules, x, y, memory cells) with both image.data and image.gain
        # for raw data and only image.data for calibrated data
        # When reading from a streamed file it looks like
        # (memory cells, 2, x, y) for raw data and
        # (memory cells, x, y) for calibrated data
        # Information confirmed by EXtra-foam
        # https://github.com/European-XFEL/EXtra-foam/blob/dev/extra_foam/pipeline/processors/image_assembler.py
        if(obj['image.data'].shape[-2] == 512 and obj['image.data'].shape[-1] == 128):
            # We're dealing with file streamed data
            # Reshape it to look like live data
            if obj['image.data'].ndim == 4:
                # looks like raw data
                if self._data_format != 'Raw':
                    logging.error('AGIPD data looks raw but self._data_format says otherwise!')
                    return
                # Add a dummy dimension for the module number
                img = obj['image.data'][numpy.newaxis]
                # Transpose to look like live data
                img = numpy.transpose(img[:,cells,...], (0, 2, 3, 4, 1))
            elif obj['image.data'].ndim == 3:
                # looks like calibrated data
                if self._data_format != 'Calib':
                    logging.error('AGIPD data looks calibrated but self._data_format says otherwise!')
                    return
                                # Add a dummy dimension for the module number
                img = obj['image.data'][numpy.newaxis]
                img = numpy.transpose(img[:,cells,...], (0, 2, 3, 1))

        elif(obj['image.data'].shape[-3] == 512 and obj['image.data'].shape[-2] == 128):
            # We're dealing with live data
            # No need to tranpose            
            img = obj['image.data'][...,cells]
            if img.ndim == 3:
                img = img[numpy.newaxis]
            assert img.ndim == 4
            
            # If data is raw, add the gain reference along the 0th dimension
            if self._data_format == 'Raw':
                gain = obj['image.gain'][...,cells]
                if gain.ndim == 3:
                    gain = gain[numpy.newaxis]                
                img = numpy.concatenate((img, gain), axis=0)
            # If data is calibrated there is no need to look at the gain
            elif self._data_format == 'Calib':
                pass
            else:
                raise NotImplementedError("DataFormat should be 'Calib' or 'Raw''")
        else:
            raise ValueError("image.data does not have a known shape!")
        add_record(values, 'photonPixelDetectors', self._s2c[evt_key], img, ureg.ADU)


    def _tr_DSSC(self, values, obj, evt_key):
        """Translates an DSSC detector or module into Humminbird ADU array"""
        if('image.pulseId' not in obj or 'image.data' not in obj):
            logging.warning('Could not find an DSSC data')
            return
        cellid = numpy.squeeze(obj["image.cellId"]).astype(int)
        cells = numpy.in1d(cellid, self._use_cells)
        # When reading from the real live data stream the data looks like
        # (modules, x, y, memory cells) with both image.data and image.gain
        # for raw data and only image.data for calibrated data
        # When reading from a streamed file it looks like
        # (memory cell, 1, y, x) for raw data and
        # (memory cells, y, x) for calibrated data
        # Information confirmed by EXtra-foam
        # https://github.com/European-XFEL/EXtra-foam/blob/dev/extra_foam/pipeline/processors/image_assembler.py
        if(obj['image.data'].shape[-2] == 128 and obj['image.data'].shape[-1] == 512):
            # We're dealing with file streamed data
            # Reshape it to look like live data
            if obj['image.data'].ndim == 4:
                # looks like raw data
                if self._data_format != 'Raw':
                    logging.error('DSSC data looks raw but self._data_format says otherwise!')
                    return
                img = obj['image.data'][numpy.newaxis]
                # Transpose to look like live data
                img = numpy.transpose(img[:,cells, 0, ...], (0, 3, 2, 1))
            elif obj['image.data'].ndim == 3:
                # looks like calibrated data
                if self._data_format != 'Calib':
                    logging.error('DSSC data looks calibrated but self._data_format says otherwise!')
                    return
                img = obj['image.data'][numpy.newaxis]
                img = numpy.transpose(img[:,cells,...], (0, 3, 2, 1))

        elif(obj['image.data'].shape[-3] == 512 and obj['image.data'].shape[-2] == 128):
            # We're dealing with live data
            # No need to tranpose            
            img = obj['image.data'][...,cells]
        else:
            raise ValueError("image.data does not have a known shape!")
        assert img.ndim == 4
        add_record(values, 'photonPixelDetectors', self._s2c[evt_key], img, ureg.ADU)                
        
    def _tr_pnCCD(self, values, obj, evt_key):
        """Translates pnCCD into Humminbird ADU array"""
        if 'data.image' not in obj:
            return
        img  = obj['data.image'][...].squeeze()
        add_record(values, 'photonPixelDetectors', self._s2c[evt_key], img, ureg.ADU)


    def _tr_photon_detector(self, values, obj, evt_key):
        """Translates pixel detector into Humminbird ADU array"""
        if('DET_DSSC1M' in evt_key):
            self._tr_DSSC(values, obj, evt_key)
        elif('DET_AGIPD1M' in evt_key):
            self._tr_AGIPD(values, obj, evt_key)
        elif('PNCCD1MP' in evt_key):
            self._tr_pnCCD(values, obj, evt_key)
        else:
            raise ValueError("Unknown photon detector %s", evt_key)





    def _tr_event_id(self, values, obj):
        """Translates euxfel train event ID from data source into a hummingbird one"""
        if 'timestamp' in obj:
            timestamp = numpy.asarray(float(obj['timestamp']))
        else:
            logging.warning('Could not find timestamp information. Faking it...')
            timestamp = numpy.asarray(time.time())

        if 'image.pulseId' in obj:
            pulseid = numpy.squeeze(obj["image.pulseId"]).astype(int)
            cellid = numpy.squeeze(obj['image.cellId']).astype(int)
            train_length = len(pulseid)
            cells = numpy.in1d(cellid, self._use_cells)
            pulseid = pulseid[cells]
            # The denominator here is totally arbitrary, just we have different timestamps for different pulses
            timestamp = timestamp + (pulseid / 27000.)
            rec = Record('Timestamp', timestamp, ureg.s)
            rec.pulseId = pulseid
            rec.cellId   = cellid[cells]
            rec.badCells = cellid[~cells]
            rec.timestamp = timestamp
        else:
            rec = Record('Timestamp', timestamp, ureg.s)
            rec.timestamp = timestamp
            
        values[rec.name] = rec

    def _tr_gmd(self, values, obj, evt_key):
        sase3 = obj['data.intensitySa3TD']
        add_record(values, 'GMD', 'SASE3', sase3, ureg.ADU)

        sase1 = obj['data.intensitySa1TD']
        add_record(values, 'GMD', 'SASE1', sase1, ureg.ADU)
        
    def _tr_trace_sqs_pnccd(self, values, obj, evt_key):
        trace_dict = {'MCP': 'digitizers.channel_1_A.raw.samples'}
        for k in trace_dict.keys():
            data = obj[trace_dict[k]]
            add_record(values, 'trace', k, data, ureg.ADU)
