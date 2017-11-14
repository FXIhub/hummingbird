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
    group.add_argument('--euxfel-socket', metavar='euxfel_socket', default='tcp://127.0.0.1:4500', nargs='1',
                        help="run number",
                        type=int)
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
        result = EventTranslator(evt, self)
        
        self._pos++
        return result

    def event_keys(self, evt):
        """Returns the translated keys available"""
        # TODO
        native_keys = evt.keys()
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
        return evt.keys()

    def translate(self, evt, key):
        """Returns a dict of Records that match a given hummingbird key"""
        values = {}
        if(key in self._c2id_detectors):
            return self.translate_object(evt, key)
        elif(key in self._c2n):
            return self.translate_core(evt, key)
        #elif(key == 'parameters'):
        #    return self._tr_epics()
        elif(key == 'analysis'):
            return {}
        elif(key == 'stream'):
            return {}
        else:
            # check if the key matches any of the existing keys in the event
            event_keys = evt.keys()
            values = {}
            found = False
            for event_key in event_keys:
                if(event_key.key() == key):
                    obj = evt.get(event_key.type(), event_key.src(), event_key.key())
                    found = True
                    add_record(values, 'native', '%s[%s]' % (self._s2c[str(event_key.src())], key),
                               obj, ureg.ADU)
            if(found):
                return values
            else:
                print '%s not found in event' % (key)

    def translate_object(self, evt, key):
        # TODO
        values = {}
        detid = self._c2id_detectors[key]
        if detid in PNCCD_IDS:
            det = self._detectors[detid]
            obj = self._detectors[detid]['obj']
            data_nda = det['data_method'](obj, evt)
            if data_nda is None:
                image = None
            elif len(data_nda.shape) <= 2:
                image = data_nda
            elif len(data_nda.shape) == 3:
                image = numpy.hstack([numpy.vstack([data_nda[0],data_nda[1][::-1,::-1]]),
                                      numpy.vstack([data_nda[3],data_nda[2][::-1,::-1]])])
            add_record(values, det['type'], det['key'], image, ureg.ADU)
        elif detid in ACQ_IDS:
            det = self._detectors[detid]
            # waveforms are in Volts, times are in Seconds
            obj = det['obj']
            waveforms = obj.waveform(evt)
            #print "waveforms", waveforms
            #times = obj.wftime(evt)
            for i, wf in enumerate(waveforms):
                add_record(values, det['type'], det['keys'][i], wf, ureg.V)
        else:
            raise RuntimeError('%s not yet supported' % key)
        return values

    def event_id(self, evt):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        # TODO
        return self.translate(evt, 'eventID')['Timestamp'].timestamp

    def event_id2(self, evt):
        """Returns the LCLS time, a 64-bit integer as an alterative ID"""
        # TODO. Should we exist?
