# --------------------------------------------------------------------------------------
# Copyright 2017, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Online backend for reading EUxfel events from zmq."""
from __future__ import print_function # Compatibility with python 2 and 3
import os
import logging
from backend.event_translator import EventTranslator
from backend.record import Record, add_record
import numpy
import datetime
from pytz import timezone
from . import ureg
from backend import Worker
import ipc
import zmq
import msgpack
import msgpack_numpy
msgpack_numpy.patch()
import time as timemodule

from hummingbird import parse_cmdline_args


_argparser = None
def add_cmdline_args():
    global _argparser
    from utils.cmdline_args import argparser
    _argparser = argparser
    #group = _argparser.add_argument_group('EUxfel', 'Options for the EUxfel event translator')
    #group.add_argument('--euxfel-socket', metavar='euxfel_socket', default='tcp://127.0.0.1:4500',
    #                    help="EuXFEL socket address",
    #                    type=str)
    # TODO
    #group.add_argument('--euxfel-number-of-frames', metavar='euxfel_number_of_frames', nargs='?',
    #                    help="number of frames to be processed",
    #                    type=int)


class EUxfelTranslator(object):
    """Translate between EUxfel events and Hummingbird ones"""
    """Note: Karabo provides full trains. We extract pulses from those."""
    def __init__(self, state):

        # Hack for timing
        self.t0 = timemodule.time()
        self.ntrains = 0

        self.timestamps = None
        cmdline_args = _argparser.parse_args()
        self._source = state['euxfel/agipd']
        
        # Reading data over ZMQ using socket adress (this is blocking, so this backend only works with one source at a time)
        self._zmq_context = zmq.Context()
        self._zmq_request = self._zmq_context.socket(zmq.REQ)
        self._zmq_request.connect(self._source['socket'])

        # Counters
        self._num_read_ahead = 1
        self._pos = 0
        self._pulsecount = None
        self._data = None
        self._asked_data = False
        self.library = 'EUxfel'

        # Define how to translate between euxfel keys and Hummingbird ones
        # TODO: pulseEnergies, photonEnergies, train meta data, ..., ...        
        # AGIPD
        self._n2c = {}
        self._mainsource = self._source['source']
        # Using the AGIPD metadata as our master source of metadata
        self._n2c[self._mainsource] = ['photonPixelDetectors', 'eventID']
        

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
        # AGIPD
        self._s2c[self._mainsource] = self._mainsource

    def check_asked_data(self):
        """"Call for new data if needed."""
        if self._asked_data:
            return

        if self._data is None or (self._pos >= self._pulsecount - self._num_read_ahead):
            self._zmq_request.send(b'next')
            self._asked_data = True
            
    def next_event(self):
        """Grabs the next event and returns the translated version"""           
        # Old comment from Onda
        # FM: When running with vetoeing we get data on cells 2,4,6...,28
        # corresponding to indices 4,8,...,56
        if self._data is None or self._pos == self._pulsecount:
            self.check_asked_data()
            msg = self._zmq_request.recv()
            self._data = msgpack.loads(msg)
            self._asked_data = False
            self._pos = 0
            self._pulsecount = len(self._data[self._mainsource]['image.pulseId'].squeeze())
            self.ntrains += 1.
            #print("Train count: ", self.ntrains)
            #print("Trains per sec: ",self.ntrains / (timemodule.time()-self.t0))

        self.check_asked_data()
        result = EventTranslator((self._pos, self._data), self)

        # Update pulse position counter
        self._pos = self._pos + 1
        
        return result

    def event_keys(self, evt):
        """Returns the translated keys available"""
        native_keys = evt[1].keys()
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
                print('%s not found in event' % (key))

    def translate_core(self, evt, key):
        """Returns a dict of Records that matchs a core Hummingbird key.

        Core keys include  all except: parameters, any psana create key,
        any native key."""
        values = {}
        #print(evt,evt[0],evt[1])
        for k in self._c2n[key]:
            if k in evt[1]:
                if key == 'eventID':
                    self._tr_event_id(values, evt[1][k], evt[0])
                elif key == 'photonPixelDetectors':
                    self._tr_photon_detector(values, evt[1][k], k, evt[0])
                else:
                    raise RuntimeError('%s not yet supported with key %s' % (k, key))
                
        return values

    def event_id(self, evt):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        return self.translate(evt, 'eventID')['Timestamp'].timestamp

    def event_id2(self, evt):
        """Returns the int64 pulse ID"""
        return self.translate(evt, 'eventID')['Timestamp'].timestamp2

    def _tr_photon_detector(self, values, obj, evt_key, pos):
        """Translates pixel detector into Humminbird ADU array"""
        if self._source['format'] == 'combined':
            img = obj['image.data'][pos]
        elif self._source['format'] == 'panel':
            img = obj['image.data'][:,:,0,pos]
        add_record(values, 'photonPixelDetectors', self._s2c[evt_key], img, ureg.ADU)

    def _tr_event_id(self, values, obj, pos):
        """Translates euxfel event ID from some source into a hummingbird one"""
        src_timestamp = obj['metadata']['timestamp']
        #print(src_timestamp, pos)
        timestamp = src_timestamp['sec'] + src_timestamp['frac'] * 1e-18 + pos * 1e-2
        #print(timestamp)
        #print(timemodule.time()-timestamp)
        time = datetime.datetime.fromtimestamp(timestamp, tz=timezone('utc'))
        time = time.astimezone(tz=timezone('CET'))
        rec = Record('Timestamp', time, ureg.s)
        rec.pulseCount = self._pulsecount
        rec.pulseNo = pos       
        rec.timestamp = timestamp
        values[rec.name] = rec
