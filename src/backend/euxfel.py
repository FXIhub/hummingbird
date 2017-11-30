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
import pickle

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

        self._slow_data = None
        if "slow_data_file" in self._source:
            self._slow_data_file = self._source["slow_data_file"]
        else:
            self._slow_data_file = None
        
        # Reading data over ZMQ using socket adress (this is blocking, so this backend only works with one source at a time)
        self._zmq_context = zmq.Context()
        self._zmq_request = self._zmq_context.socket(zmq.REQ)
        self._zmq_request.connect(self._source['socket'])

        # Slow data zmq
        if "slow_data_socket" in self._source:
            self._zmq_context_slow_data = zmq.Context()
            self._zmq_request_slow_data = self._zmq_context_slow_data.socket(zmq.REQ)
            self._zmq_request_slow_data.connect(self._source["slow_data_socket"])
            self._zmq_request_slow_data.RCVTIMEO = 1000
        else:
            self._zmq_request_slow_data = None

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
        self._n2c[self._mainsource] = ['photonPixelDetectors', 'eventID', 'slowData']
        

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
        # Request new train
        if self._data is None or self._pos == self._pulsecount:
            self.check_asked_data()
            msg = self._zmq_request.recv()
            self._data = msgpack.loads(msg)

            #import pickle
            #pickle.dump(self._data, open("dump_3ch0.p", "wb"))
            #import sys
            #print("exiting")
            #sys.exit(1)

            # # Read slow data once per pulse train
            # if (self._slow_data_file is not None and
            #     os.path.isfile(self._slow_data_file)):
            #     try:
            #         data_read = False
            #         while not data_read:
            #             with open(self._slow_data_file, "rb") as file_handle:
            #                 self._slow_data = pickle.load(file_handle)
            #                 data_read = True
            #                 #print(self._slow_data)
            #                 # print("slow data read")
            #                 # import sys
            #                 # sys.exit(1)
            #     except IOError:
            #         pass

            # Receive slow data once per pulse train
            
            if self._zmq_request_slow_data is not None:
                self._zmq_request_slow_data.send(b'next')
                msg = self._zmq_request_slow_data.recv()
                #print(msg[:100])
                self._slow_data = msgpack.loads(msg)

            self._asked_data = False
            self._pulsecount = len(self._data[self._mainsource]['image.pulseId'].squeeze())
            self._pos = 0
        self.check_asked_data()

        # For the combined data, pulses are filtered, but a train only has 30 pulses, drop the rest of the frames
        if self._source['format'] == 'combined':
            if self._pos >= 30:
                self._pos += 1 # Update pulse position counter
                raise IndexError
        # Pulses are unfiltered, drop the first 2 frames, keep every second frame up to 30 pulses, drop the rest
        elif self._source['format'] == 'panel':
            valid_pos = range(2,64-2,2)
            if self._pos not in valid_pos:
                self._pos += 1 # Update pulse position counter
                raise IndexError

        # Translate valid pulses
        result = EventTranslator((self._pos, self._data, self._slow_data), self)
        self._pos += 1 # Update pulse position counter
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
                elif key == 'slowData':
                    self._tr_slow_data(values, evt[2])
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
            # Currently, the data has shape (panel, ny, nx) = (16,512,128)
            # should be extented to (mode, panel, ny, nx) = (2,16,512,128)
            img_values = obj['image.data'][pos]
            gain = obj['image.gain'][pos]
            img = numpy.vstack((img_values[numpy.newaxis, ...],
                                gain[numpy.newaxis, ...]))
            
        elif self._source['format'] == 'panel':
            # Reshape data such that it becomes (mode, panel, ny, nx) = (2,1,512,128)
            img = numpy.rollaxis(obj['image.data'][:,:,:,pos], 2)
            #img = numpy.ascontiguousarray(img.reshape((img.shape[0], 1, img.shape[1], img.shape[2])))
            img = numpy.ascontiguousarray(img.reshape((2, 1, 512, 128)))
            assert img.shape[0] == 2
            assert img.shape[1] == 1
            assert img.shape[2] == 512
            assert img.shape[3] == 128
        add_record(values, 'photonPixelDetectors', self._s2c[evt_key], img, ureg.ADU)

    def _tr_event_id(self, values, obj, pos):
        """Translates euxfel event ID from some source into a hummingbird one"""
        src_timestamp = obj['metadata']['timestamp']
        timestamp = src_timestamp['sec'] + src_timestamp['frac'] * 1e-18 + pos * 1e-2
        time = datetime.datetime.fromtimestamp(timestamp, tz=timezone('utc'))
        time = time.astimezone(tz=timezone('CET'))
        rec = Record('Timestamp', time, ureg.s)
        rec.pulseCount = self._pulsecount
        rec.pulseNo = pos
        rec.pulseId = obj['image.pulseId'][0, pos]
        rec.cellId  = obj['image.cellId'][0, pos]
        rec.trainId = obj['header.trainId']
        rec.timestamp = timestamp
        values[rec.name] = rec

    def _tr_slow_data(self, values, slow_data):
        # rec = Record("slowData", 0., ureg.s)
        # rec.full_dict = self._slow_data
        # values[rec.name] = rec
        # print(self._slow_data)
        # import sys
        # sys.exit(1)
        add_record(values, "slowData", "full_dict", self._slow_data, None)
        #values[rec.name, 
        
