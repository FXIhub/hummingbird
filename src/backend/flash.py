# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Creates Hummingbird events for testing purposes"""
import time
import random
from backend.event_translator import EventTranslator
from backend.record import add_record
from backend import Worker
from . import ureg
import numpy
import ipc
import backend.convert_frms6 as convert
import backend.holger_motors as holger_motors
import glob
import sys
import os
import h5py

class FLASHTranslator(object):
    """Creates Hummingbird events for testing purposes"""
    def __init__(self, state):
        self.library = 'FLASH'
        self.state = state
        self.keys = set()
        self.keys.add('analysis')
        self._last_event_time = -1
        self.current_fname = None
        self.current_dark = None
        self.offset = None
        self.get_dark()
        self.motors = holger_motors.MotorPositions(state['FLASH/MotorFolder'])

    def next_event(self):
        """Generates and returns the next event"""
        evt = {}        
        
        self.new_file_check()
        
        # Check if we need to sleep
        if(self._last_event_time > 0):
            rep_rate = 1e9
            if('Dummy' in self.state and 'Repetition Rate' in self.state['Dummy']):
                rep_rate = self.state['Dummy']['Repetition Rate'] / float(ipc.mpi.nr_workers())
            target_t = self._last_event_time+1.0/rep_rate
            t = time.time()
            if(t < target_t):
                time.sleep(target_t - t)
        self._last_event_time = time.time()
        
        self.reader.parse_frames(start_num=ipc.mpi.slave_rank()+self.num*(ipc.mpi.size-1), num_frames=1)
        if len(self.reader.frames) > 0:
            evt['pnCCD'] = self.reader.frames[0]
            self.keys.add('photonPixelDetectors')
        else:
            while True:
                while not self.new_file_check():
                    if ipc.mpi.slave_rank() == 0:
                        sys.stderr.write('\rWaiting for file list to update')
                    time.sleep(2.)
                sys.stderr.write('\n')
                self.reader.parse_frames(start_num=ipc.mpi.slave_rank()+self.num*(ipc.mpi.size-1), num_frames=1)
                if len(self.reader.frames) > 0:
                    evt['pnCCD'] = self.reader.frames[0]
                    self.keys.add('photonPixelDetectors')
                    break

        self.num += 1
        return EventTranslator(evt, self)

    def event_keys(self, _):
        """Returns the translated keys available"""
        return list(self.keys)

    def event_native_keys(self, evt):
        """Returns the native keys available"""
        return evt.keys()

    def translate(self, evt, key):
        """Returns a dict of Records that match a given Humminbird key"""
        values = {}
        if key == 'photonPixelDetectors':
            # Translate pnCCD
            add_record(values, key, 'pnCCD', evt['pnCCD'], ureg.ADU)
        elif key == 'motorPositions':
            val = self.motors.get(self.reader.frame_headers[-1].tv_sec)
            if val is None:
                raise RuntimeError('%s not found in event' % key)
            for motorname,motorpos in val.iteritems():
                add_record(values, key, motorname, motorpos, ureg.mm)
        elif key == 'ID':
            add_record(values, key, 'DataSetID', self.reader.file_header.dataSetID.rstrip('\0'))
            add_record(values, key, 'BunchID', self.reader.frame_headers[-1].external_id)
            add_record(values, key, 'tv_sec', self.reader.frame_headers[-1].tv_sec)
            add_record(values, key, 'tv_usec', self.reader.frame_headers[-1].tv_usec)
        elif not key == 'analysis':
            raise RuntimeError('%s not found in event' % key)
        
        return values

    def event_id(self, _):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        return float(time.time())

    def event_id2(self, _):
        """Returns an alternative id, which is jsut a copy of the usual id here"""
        return event_id

    def new_file_check(self):
        flist = glob.glob(self.state['FLASH/DataFolder'] + '/*.frms6')
        latest_fname = max(flist, key=os.path.getmtime)
        if latest_fname != self.current_fname:
            # Check if file is too small
            if os.path.getsize(latest_fname) < 1024:
                return False
            print 'Found new file', latest_fname
            self.get_dark()
            # Parse file header and reset self.num
            self.reader = convert.Frms6_reader(latest_fname, offset=self.offset)
            self.num = 0
            self.current_fname = latest_fname
            self.current_mtime = os.path.getmtime(latest_fname)
            return True
        elif os.path.getmtime(latest_fname) != self.current_mtime:
            # Check if the same file has been updated since the last check
            return True
        else:
            return False
        
    def get_dark(self):
        flist = glob.glob(self.state['FLASH/CalibFolder']+'/*.darkcal.h5')
        if len(flist) == 0:
            self.offset = None
            return False
        
        latest_fname = max(flist, key=os.path.getmtime)
        if latest_fname != self.current_dark and os.path.getsize(latest_fname) > 1024**2:
            print 'Found new dark file', latest_fname
            self.current_dark = latest_fname
            with h5py.File(latest_fname, 'r') as f:
                self.offset = f['data/offset'][:]
            return True
        else:
            return False
