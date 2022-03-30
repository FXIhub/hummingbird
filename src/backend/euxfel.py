# --------------------------------------------------------------------------------------
# Copyright 2017, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Online backend for reading EuXFEL events via the Karabo-bridge."""
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

MAX_TRAIN_LENGTH = 352

class EUxfelTranslator():
    """Translate between EUxfel events and Hummingbird ones"""
    def __init__(self, state):
        self.timestamps = None
        self.library = 'karabo_bridge'

        # Read the main data source, e.g. AGIPD
        if 'EuXFEL/DataSource' in state:
            dsrc = state['EuXFEL/DataSource']
        elif('EuXFEL' in state and 'DataSource' in state['EuXFEL']):
            dsrc = state['EuXFEL']['DataSource']
        else:
            raise ValueError("You need to set the '[EuXFEL][DataSource]'"
                             " in the configuration")

        # The data format for the data source, either "Calib" or "Raw"
        self._data_format = "Calib"
        if 'EuXFEL/DataFormat' in state:
            self._data_format = state["EuXFEL/DataFormat"]
        if not self._data_format in ["Calib", "Raw"]:
            raise ValueError("You need to set the 'EuXFEL/DataFormat'"
                             " in the configuration as 'Calib' or 'Raw'")
            
        self._sel_module = state['EuXFEL/SelModule'] if 'EuXFEL/SelModule' in state else None
        self._max_train_age = state['EuXFEL/MaxTrainAge'] if 'EuXFEL/MaxTrainAge' in state else 5 # seconds
        first_cell = state['EuXFEL/FirstCell'] if 'EuXFEL/FirstCell' in state else 1
        last_cell = state['EuXFEL/LastCell'] if 'EuXFEL/LastCell' in state else -1
        bad_cells = state['EuXFEL/BadCells'] if 'EuXFEL/BadCells' in state else []
        slsrc = state['EuXFEL/SlowSource'] if 'EuXFEL/SlowSource' in state else None
        self._slow_keys = state['EuXFEL/SlowKeys'] if 'EuXFEL/SlowKeys' in state else None
        self._slow_update_rate = state['EuXFEL/SlowUpdate'] if 'EuXFEL/SlowUpdate' in state else 1

        # Cell filter
        self._cell_filter = numpy.zeros(MAX_TRAIN_LENGTH, dtype='bool')
        self._cell_filter[first_cell:last_cell] = True
        for cell in bad_cells:
            self._cell_filter[cell] = False

        # Start Karabo client for data source(s)
        #self._data_client = karabo_bridge.Client(dsrc)
        if not isinstance(dsrc, list):
            dsrc = [dsrc]
        self._data_clients = [karabo_bridge.Client(s, 'PULL') for s in dsrc]
        
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
        for module_index in range(16):
            self._n2c["SPB_DET_AGIPD1M-1/DET/%dCH0:xtdf"%module_index] = ['photonPixelDetectors', 'eventID']
        self._n2c["SQS_NQS_PNCCD1MP/CAL/PNCCD_FMT-0:output"] = ['photonPixelDetectors', 'eventID']
        self._n2c["SA3_XTD10_XGM/XGM/DOOCS:output"] = ['GMD', 'eventID']
        # self._n2c["SQS_NQS_PNCCD1MP/CAL/CORR_CM:dataOutput"] = ['photonPixelDetectors', 'eventID']
        # self._n2c["SQS_NQS_PNCCD1MP/CAL/PNCCD_FMT-1:output"] = ['photonPixelDetectors', 'eventID']

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
        if self._sel_module is None:
            self._s2c["SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED"] = "AGIPD"
            self._s2c["SPB_DET_AGIPD1M-1/CAL/APPEND_RAW"] = "AGIPD"
            for module_index in range(16):
                self._s2c["SPB_DET_AGIPD1M-1/DET/%dCH0:xtdf"%module_index] = "AGIPD%.2d" % module_index
        else:
            self._s2c["SPB_DET_AGIPD1M-1/DET/%dCH0:xtdf"%self._sel_module] = "AGIPD"
        
        self._s2c["SQS_NQS_PNCCD1MP/CAL/PNCCD_FMT-0:output"] = "pnCCD"
        # self._s2c["SQS_NQS_PNCCD1MP/CAL/PNCCD_FMT-1:output"] = "pnCCD"
        
        self._s2c["SA3_XTD10_XGM/XGM/DOOCS:output"] = "GMD"

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
        buf = {}
        meta = {}
        for client in self._data_clients:
            buf_n, meta_n = client.next()
            buf.update(buf_n)
            meta.update(meta_n)
        # print("got data")

        if(self._slow_client is not None): 
            buf, meta = self.append_slow_data(buf, meta)
       
        # age = numpy.floor(time.time()) - int(meta[list(meta.keys())[0]]['timestamp.sec'])
        age = numpy.floor(time.time()) - int(meta[list(meta.keys())[0]]['timestamp.tid'])
        if age < self._max_train_age:
            return buf, meta
        else:
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
                    if 'AGIPD' in self._s2c[k]:
                        self._tr_event_id_spb(values, evt[k])
                    elif self._s2c[k] == 'pnCCD':
                        self._tr_event_id_sqs_pnccd(values, evt[k])
                elif key == 'photonPixelDetectors':
                    if 'AGIPD' in self._s2c[k]:
                        self._tr_photon_detector_spb(values, evt[k], k)
                    elif self._s2c[k] == 'pnCCD':
                        self._tr_photon_detector_sqs_pnccd(values, evt[k], k)
                elif key == 'GMD':
                    self._tr_gmd_sqs_pnccd(values, evt[k], k)
                elif key == "trace":
                    self._tr_trace_sqs_pnccd(values, evt[k], k)
                else:
                    raise RuntimeError('%s not yet supported with key %s' % (k, key))
        return values


class EUxfelTrainTranslator(EUxfelTranslator):
    """Translate between EUxfel train events and Hummingbird ones"""
    def __init__(self, state):
        super().__init__(state)
          
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
    
    def _tr_photon_detector_spb(self, values, obj, evt_key):
        """Translates pixel detector into Humminbird ADU array"""
        '''
        train_length = numpy.array(obj["image.pulseId"]).shape[-1]
        cells = self._cell_filter[:train_length]
        img  = obj['image.data'][..., cells]
        gain = obj['image.gain'][..., cells]
        if self._sel_module is not None:
            img = img[numpy.newaxis]
        assert img.ndim == 4
        if self._sel_module is not None:
            gain = gain[numpy.newaxis] 
 
        # If data is raw, add the gain reference along the 0th dimension
        if self._data_format == 'Raw':
            assert gain.ndim == 4
            img = numpy.concatenate((img, gain), axis=0)
        # If data is calibrated there is no need to look at the gain
        elif self._data_format == 'Calib':
            pass
        else:
            raise NotImplementedError("DataFormat should be 'Calib' or 'Raw''")
        add_record(values, 'photonPixelDetectors', self._s2c[evt_key], img, ureg.ADU)
        '''

        if "image.data" not in obj.keys():
            return
        img  = obj['image.data'][...].squeeze()
        add_record(values, 'photonPixelDetectors', self._s2c[evt_key], img, ureg.ADU)

    def _tr_photon_detector_sqs_pnccd(self, values, obj, evt_key):
        """Translates pixel detector into Humminbird ADU array"""
        img  = obj['data.image'][...].squeeze()
        # print("raw image shape", img.shape)
        add_record(values, 'photonPixelDetectors', self._s2c[evt_key], img, ureg.ADU)

    def _tr_event_id_spb(self, values, obj):
        """Translates euxfel train event ID from data source into a hummingbird one"""
        '''
        train_length = numpy.array(obj["image.pulseId"]).shape[-1]
        cells = self._cell_filter[:train_length]
        pulseid  = numpy.array(obj["image.pulseId"][..., cells], dtype='int') #doesnt exist for pnccd
        tsec  = numpy.array(obj['timestamp.sec'], dtype='int') 
        tfrac = numpy.array(obj['timestamp.frac'], dtype='int') * 1e-18 
        timestamp = tsec + tfrac + (pulseid / 760.)
        time = numpy.array([datetime.datetime.fromtimestamp(t, tz=timezone('utc')) for t in timestamp])
        rec = Record('Timestamp', time, ureg.s)
        rec.pulseId = pulseid
        rec.cellId   = numpy.array(obj['image.cellId'][...,  cells], dtype='int')
        rec.badCells = numpy.array(obj['image.cellId'][..., ~cells], dtype='int')
        '''
        timestamp = numpy.array(float(obj['timestamp']))
        rec = Record('Timestamp', timestamp, ureg.s)
        # rec.trainId  = [numpy.array(obj['data.trainId'], dtype='int')]
        rec.timestamp = [timestamp]
        values[rec.name] = rec

    def _tr_event_id_sqs_pnccd(self, values, obj):
        """Translates euxfel train event ID from data source into a hummingbird one"""
        timestamp = numpy.array(obj['timestamp.tid'], dtype='int')

        rec = Record('Timestamp', timestamp, ureg.s)
        # rec.trainId  = [numpy.array(obj['data.trainId'], dtype='int')]
        rec.timestamp = [timestamp]
        values[rec.name] = rec

    def _tr_gmd_sqs_pnccd(self, values, obj, evt_key):
        sase_3_pulse_index = 0
        # print("obj.keys()", obj.keys())
        sase3 = obj['data.intensitySa3TD'][sase_3_pulse_index]
        add_record(values, 'GMD', 'SASE3', sase3, ureg.ADU)

        sase_1_train_length = 176
        sase1 = obj['data.intensitySa1TD'][:sase_1_train_length]
        add_record(values, 'GMD', 'SASE1', sase1, ureg.ADU)
        
    def _tr_trace_sqs_pnccd(self, values, obj, evt_key):
        trace_dict = {'MCP': 'digitizers.channel_1_A.raw.samples'}
        for k in trace_dict.keys():
            data = obj[trace_dict[k]]
            add_record(values, 'trace', k, data, ureg.ADU)

class EUxfelPulseTranslator(EUxfelTranslator):
    """Translate between EUxfel pulse events and Hummingbird ones"""
    def __init__(self, state):
        super().__init__(state)
        self._train_buffer = None
        self._train_meta = None
        self._remaining_pulses = 0
        self._good_cells = None

        # Option to skip pulses within a train
        self._skip_n_pulses = 0
        if 'EuXFEL/SkipNrPulses' in state:
            self._skip_n_pulses = state['EuXFEL/SkipNrPulses']

    def next_event(self):
        """Grabs the next event returns the translated version."""
        # If no remaining pulses in the buffer:
        #   Gets next train from Karabo Bridge
        #   Resets number of remaining pulses
        if not self._remaining_pulses:
            self._train_buffer, self._train_meta = self.next_train()
            # self._train_id = self._train_buffer[list(self._train_buffer.keys())[0]]['image.trainId']
            # self._train_id = self._train_buffer["SQS_NQS_PNCCD1MP/CAL/PNCCD_FMT-1:output"]['data.trainId']
            # self._train_length = len(self._train_id)
            self._remaining_pulses = self._train_length
            self._good_cells = self._cell_filter[:self._train_length]

        # If pulses still remaining in the buffer:
        #   Sets current event to first remaining pulse
        #   Populates event dictionary
        
        if self._remaining_pulses:
            index = self._train_length - self._remaining_pulses
            if not self._good_cells[index]:
                self._remaining_pulses -= 1
                return self.next_event()
            evt = {}
            for source, d in self._train_meta.items():
                evt[source] = {}
                for k,v in self._train_buffer[source].items():
                    if type(v) is list:
                        continue
                    evt[source][k] = v[...,index]
                for k,v in d.items():
                    evt[source][k] = v
            # Update remaining pulses, skipping some pulses if requested
            self._remaining_pulses = max(0, self._remaining_pulses - (1 + self._skip_n_pulses))

        return EventTranslator(evt, self)

    def event_id(self, evt):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        return self.translate(evt, 'eventID')['Timestamp'].timestamp
    
    def _tr_photon_detector(self, values, obj, evt_key):
        """Translates pixel detector into Humminbird ADU array"""
        img = obj['image.data']
        gain = obj['image.gain']
        if self._sel_module is not None:
            img = img[numpy.newaxis]
        if self._sel_module is not None:
            gain = gain[numpy.newaxis]
        # If data is raw, add the gain reference along the 0th dimension
        if self._data_format == 'Raw':
            img = numpy.concatenate((img, gain), axis=0)
        # If data is calibrated there is no need to look at the gain
        elif self._data_format == 'Calib':
            pass
        else:        
            raise NotImplementedError("DataFormat should be 'Calib' or 'Raw''")
        add_record(values, 'photonPixelDetectors', self._s2c[evt_key], img, ureg.ADU)
        
    def _tr_event_id(self, values, obj):
        """Translates euxfel event ID from some source into a hummingbird one"""
        pulseid = int(obj["image.pulseId"])
        # timestamp = int(obj['timestamp.sec']) + int(obj['timestamp.frac']) * 1e-18 + pulseid * 1e-2
        timestamp = int(obj['timestamp.tid']) + pulseid * 1e-2
        time = datetime.datetime.fromtimestamp(timestamp, tz=timezone('utc'))
        time = time.astimezone(tz=timezone('CET'))
        rec = Record('Timestamp', time, ureg.s)
        # rec.pulseId = int(obj['image.pulseId'])
        # rec.cellId  = int(obj['image.cellId'])
        # rec.trainId = int(obj['data.trainId'])
        rec.timestamp = timestamp
        values[rec.name] = rec
