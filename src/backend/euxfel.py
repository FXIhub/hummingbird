# --------------------------------------------------------------------------------------
# Copyright 2017, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Online backend for reading EUxfel events from zmq."""
import os
import logging
from backend.event_translator import EventTranslator
from backend.record import Record, add_record
import numpy
import datetime
from . import ureg
from backend import Worker
import ipc
from hummingbird import parse_cmdline_args


_argparser = None
def add_cmdline_args():
    global _argparser
    from utils.cmdline_args import argparser
    _argparser = argparser
    group = _argparser.add_argument_group('EUxfel', 'Options for the EUxfel event translator')
    group.add_argument('--euxfel-socket', metavar='euxfel_socket', default='tcp://127.0.0.1:4500', nargs=1,
                        help="run number",
                        type=string)
    # TODO
    #group.add_argument('--euxfel-number-of-frames', metavar='euxfel_number_of_frames', nargs='?',
    #                    help="number of frames to be processed",
    #                    type=int)
    
class EUxfelTranslator(object):
    """Translate between EUxfel events and Hummingbird ones"""
    """Note: Karabo provides full trains. We extract pulses from those."""
    def __init__(self, state):
        self.timestamps = None
        
        cmdline_args = _argparser.parse_args()
        # TODO
        #self.N = cmdline_args.euxfel_number_of_frames
        self._zmq_context = zmq.Context()
        self._zmq_request = self._zmq_context.socket(zmq.REQ)       
        self._zmq_request.connect(cmdline_args.euxfel_socket)
        self._num_read_ahead = 0
        self._pos = 0
        self._data = None
        self._asked_data = False

        # Define how to translate between euxfel keys and Hummingbird ones
        # TODO: pulseEnergies, photonEnergies, train meta data, ..., ...        
        # AGIPD
        self._n2c['SPB_DET_AGIPD1M-1/DET/0CH0:xtdf'] = 'photonPixelDetectors'
        # Using the AGIPD metadata as our master source of metadata
        self._n2c['SPB_DET_AGIPD1M-1/DET/0CH0:xtdf'] = 'eventID'

        # Calculate the inverse mapping
        self._c2n = {}
        for k, v in self._n2c.iteritems():
            self._c2n[v] = self._c2n.get(v, [])
            self._c2n[v].append(k)

        # Define how to translate between LCLS sources and Hummingbird ones
        self._s2c = {}
        # AGIPD
        self._s2c['SPB_DET_AGIPD1M-1/DET/0CH0:xtdf'] = 'AGIPD1'        

    def check_asked_data(self):
        """"Call for new data if needed."""
        if self._asked_data:
            return

        if self._data is None or self._pos >= self._data[self._mainsource][pulsecount] - self._num_read_ahead:
            self._zmq_request.send(b'next')
            self._asked_data = True
                    
    def next_event(self):
        """Grabs the next event and returns the translated version"""           
        # Old comment from Onda
        # FM: When running with vetoeing we get data on cells 2,4,6...,28
        # corresponding to indices 4,8,...,56
        if self._data is None or self._pos == self._data[self._mainsource][pulsecount]:
            self.check_asked_data()
            self._data = self._zmq_request.recv_pyobj()
            self._asked_data = False
            self._pos = 0

        self.checked_asked_data()
        result = EventTranslator((self._pos, _self._data), self)
        
        self._pos = self._pos + 1
        return result

    def event_keys(self, evt):
        """Returns the translated keys available"""
        # TODO
        native_keys = evt[1].keys()
        common_keys = set()
        for k in native_keys:
            for c in self._native_to_common(k):
                common_keys.add(c)
        # parameters corresponds to the EPICS values, analysis is for values added later on
        return list(common_keys)+['parameters']+['analysis']

    def _native_to_common(self, key):
        """Translates a native key to a hummingbird one"""
        if(key.type() in self._n2c):
            return [self._n2c[key.type()]]
        else:
            return []

    def event_native_keys(self, evt):
        """Returns the native keys available"""
        return evt[1].keys()

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
            event_keys = evt[1].keys()
            values = {}
            found = False

            if key in event_keys:        
                obj = evt[1][key]
                for subkey in obj.keys():
                    add_record(values, 'native', '%s[%s]' % (self._s2c[key], subkey),
                               obj[subkey], ureg.ADU)
                return values
            else:
                print '%s not found in event' % (key)

    def translate_core(self, evt, key):
        """Returns a dict of Records that matchs a core Hummingbird key.

        Core keys include  all except: parameters, any psana create key,
        any native key."""
        values = {}
        for k in self._c2n[key]:
            if k in evt[1]:
                if key == 'eventID':
                    self._tr_event_id(values, evt[1][k], evt[0])
                elif key == 'photonDetectors':
                    self._tr_photon_detector(values, evt[1][k], k)
                else:
                    print type(obj)
                    print k
                    raise RuntimeError('%s not yet supported' % (type(obj)))
                
        return values

    def event_id(self, evt):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        return self.translate(evt, 'eventID')['Timestamp'].timestamp

    def event_id2(self, evt):
        """Returns the int64 pulse ID"""
        return self.translate(evt, 'eventID')['Timestamp'].timestamp2

    def _tr_photon_detector(self, values, obj, evt_key):
        """Translates pixel detector into Humminbird ADU array"""        
        add_record(values, 'photonPixelDetectors', self._s2c[k],
                   obj['image.data'], ureg.ADU)

    def _tr_event_id(self, values, obj, pos):
        """Translates euxfel event ID from some source into a hummingbird one"""
        src_timestamp = obj['metadata']['timestamp']        
        timestamp = src_timestamp['sec'] + src_timestamp['frac'] * 1e-2 + pos * 1e-6
        time = datetime.datetime.fromtimestamp(timestamp, tz=timezone('utc'))
        time = time.astimezone(tz=timezone('CET'))
        rec = Record('Timestamp', time, ureg.s)        
        rec.fiducials = obj.fiducials()
        rec.pulseCount = obj['header.pulseCount']
        rec.pulseNo = pos       
        #rec.timestamp2 = obj['trailer.trainId']
        rec.timestamp2 = obj['image.pulseId'][rec.pulseNo]
        values[rec.name] = rec