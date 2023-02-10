# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Creates Hummingbird events for testing purposes"""
from __future__ import print_function  # Compatibility with python 2 and 3

import glob
import os
import random
import re
import sys
import time

import h5py
import numpy

from hummingbird import ipc
from . import EventTranslator, Worker, add_record, ureg
from .flash_utils import convert_frms6 as convert
from .flash_utils import read_daq_offline as read_daq
from .flash_utils import tomas_motors as motors


class FLASHTranslator(object):
    """Creates Hummingbird events for testing purposes"""
    def __init__(self, state):
        self.library = 'FLASH'
        self.state = state
        self.keys = set()
        self.keys.add('analysis')
        self.keys.add('DAQ')
        self._last_event_time = -1
        self.current_fname = None
        self.daq_fname = None
        self.current_dark = None
        self.offset = None
        self.num = None
        self.fnum = None
        self.reader = None
        self._current_event_id = None
        self.get_dark()
        self.motors = motors.MotorPositions(state['FLASH/MotorFolder'])
        self.daq = None
        if 'do_offline' in state:
            self.do_offline = state['do_offline']
        else:
            self.do_offline = False
        if "online_start_from_run" in state:
            self._online_start_from_run = state["online_start_from_run"]
        else:
            self._online_start_from_run = False
        if self.do_offline and ipc.mpi.slave_rank() == 0:
            print('Running offline i.e. on all files in glob')
        if not self.do_offline and self._online_start_from_run:
            print('Running online and starting with all files from run', self._online_start_from_run)

    def next_event(self):
        """Generates and returns the next event"""
        evt = {}
        
        self.new_file_check()
        
        # Check if we need to sleep
        if('FLASH/ProcessingRate' in self.state and self._last_event_time > 0):
            rep_rate = self.state['FLASH/ProcessingRate']
            if('Dummy' in self.state and 'Repetition Rate' in self.state['Dummy']):
                rep_rate = self.state['Dummy']['Repetition Rate'] / float(ipc.mpi.nr_workers())
            target_t = self._last_event_time+1.0/rep_rate
            t = time.time()
            if(t < target_t):
                time.sleep(target_t - t)
        self._last_event_time = time.time()

        if self.reader is not None:
            self.reader.parse_frames(start_num=ipc.mpi.slave_rank()+self.num*(ipc.mpi.size-1), num_frames=1)
        if self.reader is not None and len(self.reader.frames) > 0:
            # Observe: the following transformation has been used for pnCCD images at FLASH experiments and is currently no where implemented in the code,
            # if anything it should go into here: np.fliplr(np.flipud(image.T*mask.T))
            evt['pnCCD'] = self.reader.frames[0]
            self.keys.add('photonPixelDetectors')
            try:
                self._current_event_id = self.reader.frame_headers[0].external_id
            except AttributeError:
                self._current_event_id = None
        # self.reader.parse_frames(start_num=ipc.mpi.slave_rank()+self.num*(ipc.mpi.size-1), num_frames=1)
        # if len(self.reader.frames) > 0:
        #     evt['pnCCD'] = self.reader.frames[0]
        #     self.keys.add('photonPixelDetectors')
        else:
            if ipc.mpi.slave_rank() == 0:
                sys.stderr.write('Waiting for file list to update\n')
            while True:
                while not self.new_file_check(force=True):
                    time.sleep(.1)
                    #print('waiting for new file...')
                    if self.do_offline:
                        print('Rank %d is closing' % ipc.mpi.rank)
                        return None
                self.reader.parse_frames(start_num=ipc.mpi.slave_rank()+self.num*(ipc.mpi.size-1), num_frames=1)
                if len(self.reader.frames) > 0:
                    evt['pnCCD'] = self.reader.frames[0]
                    try:
                        self._current_event_id = self.reader.frame_headers[0].external_id
                    except AttributeError:
                        self._current_event_id = None
                    self.keys.add('photonPixelDetectors')
                    break
        #event_id += 1
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
            val = self.motors.get(self.get_bunch_time()[0])
            if val is None:
                raise RuntimeError('%s not found in event' % key)
            for motorname,motorpos in val.items():
                add_record(values, key, motorname, motorpos, ureg.mm)
        elif key == 'ID':
            add_record(values, key, 'DataSetID', self.reader.file_header.dataSetID.rstrip('\0'))
            # Sometimes BunchID is missing
            add_record(values, key, 'BunchID', self.reader.frame_headers[-1].external_id)
            add_record(values, key, 'tv_sec', self.reader.frame_headers[-1].tv_sec, ureg.s)
            add_record(values, key, 'tv_usec', self.reader.frame_headers[-1].tv_usec, ureg.s)
            add_record(values, key, 'bunch_sec', self.get_bunch_time()[0], ureg.s)
        elif key == "DAQ":
            if self.daq is None:
                self.daq = read_daq.DAQReader(self.state['FLASH/DAQBaseDir'])
            if self._current_event_id is not None:
                tof_trace = self.daq.get_tof(self._current_event_id)
                if tof_trace is not None:
                    evt["TOF"] = tof_trace
                    #self.keys.add("DAQ")
                    add_record(values, key, "TOF", evt["TOF"], ureg.s)
            else:
                raise RuntimeError("{0} not found in event".format(key))
        elif key == "FEL":
            wl = self.get_wavelength(self.get_bunch_time()[1])
            if wl is not None:
                add_record(values, key, "wavelength", wl, ureg.nm)
            else:
                raise RuntimeError("%s not found in event" %key)
            gmd = self.get_gmd(self.get_bunch_time()[1])
            if gmd is not None:
                add_record(values, key, "gmd", gmd, ureg.mJ)
            else:
                raise RuntimeError("%s not found in event" %key)
        elif not key == 'analysis':
            raise RuntimeError('%s not found in event' % key)
        
        return values

    def event_id(self, evt):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        tv_sec  = self.translate(evt, 'ID')['tv_sec'].data
        tv_usec = self.translate(evt, 'ID')['tv_usec'].data
        tv_sec_usec = tv_sec + 1e-6*tv_usec
        return tv_sec_usec

    def event_id2(self, _):
        """Returns an alternative id, which is jsut a copy of the usual id here"""
        return event_id

    def file_filter(self, filename, runnr):
        m = re.search(self.state['FLASH/DataRe'], filename)
        if not m:
            return False
        else:
            run = int(m.groups()[0])
            if run >= runnr:
                return True
            else:
                return False

    def new_file_check(self, force=False):
        flist = glob.glob(self.state['FLASH/DataGlob'])
        if self._online_start_from_run:
            flist = [f for f in flist if self.file_filter(f,self._online_start_from_run)]
        flist.sort()
        if self.do_offline or self._online_start_from_run:
            if self.fnum is None:
                self.fnum = 0
                self.flist = flist
                if ipc.mpi.is_main_event_reader():
                    print('Found %d files'% len(flist))
                if len(flist) == 0:
                    return False
            else:
                if force and ((self.fnum+1) < len(flist)):
                    self.fnum += 1
                if self.fnum == len(flist):
                    print("No more files to process", force, self.fnum)
                    return False
            latest_fname = flist[self.fnum]
            file_size = os.path.getsize(latest_fname)
        else:
            #latest_fname = max(flist, key=os.path.getmtime)
            latest_fname = sorted(flist, key=os.path.getmtime)[-2]
            file_size = os.path.getsize(latest_fname) 
            #if ipc.mpi.slave_rank() == 0:
            #    print('Glob in rank %d: latest: %s/%d' % (ipc.mpi.slave_rank(), latest_fname, file_size))
                
        
        if latest_fname != self.current_fname:
            self.current_size = file_size
            if file_size < 1024:
                return False
            if ipc.mpi.slave_rank() == 0:
                print('Rank %d found new file' % (ipc.mpi.slave_rank()), latest_fname, 'size =', self.current_size)
            self.get_dark()
            
            self.reader = convert.Frms6_reader(latest_fname, offset=self.offset)
            #print("Using dark: {0}".format(self.current_dark))
            self.num = 0
            self.current_fname = latest_fname
            return True
        elif file_size != self.current_size:
            # Check if the same file has been updated since the last check
            if ipc.mpi.slave_rank() == 0:
                print('File has changed with new size =', file_size)
            self.current_size = file_size
            return True
        else:
            return False
        
    def get_dark(self):
        flist = glob.glob(self.state['FLASH/CalibGlob'])
        if len(flist) == 0:
            self.offset = None
            return False
        
        latest_fname = max(flist, key=os.path.getmtime)
        if latest_fname != self.current_dark and os.path.getsize(latest_fname) > 1024**2:
            if ipc.mpi.slave_rank() == 0:
                print('Found new dark file', latest_fname)
            self.current_dark = latest_fname
            with h5py.File(latest_fname, 'r') as f:
                self.offset = f['data/offset'][:]
            return True
        else:
            return False

    def get_bunch_time(self):
        try:
            tmp_tvsec = self.reader.frame_headers[-1].tv_sec
        except AttributeError:
            tmp_tvsec = 0
        tmp_time = time.localtime(tmp_tvsec)
        #self.reader.frame_headers[-1].dump()
        filename = self.state['FLASH/DAQFolder']+'/daq-%.4d-%.2d-%.2d-%.2d.txt' % (tmp_time.tm_year, tmp_time.tm_mon, tmp_time.tm_mday, tmp_time.tm_hour)
        if filename != self.daq_fname:
            self.daq_fname = filename
            with open(filename, 'r') as f:
                lines = list(set(f.readlines()))
            self.daq_lines = [l.split() for l in lines]
            self.bunch_ids = numpy.array([int(l[1]) for l in self.daq_lines])
            self.wavelengths = numpy.array([float(l[2]) for l in self.daq_lines])
            try:
                self.gmds = numpy.array([float(l[3]) for l in self.daq_lines])
            except ValueError:
                self.gmds = None
            #print('DAQ file:', filename, 'max id = %d, min id = %d' % (self.bunch_ids.max(), self.bunch_ids.min()))
        locations = numpy.where(self.bunch_ids == self.reader.frame_headers[-1].external_id)[0]
        if len(locations) < 1:
            return self.reader.frame_headers[-1].tv_sec, None
        else:
            return int(self.daq_lines[locations[0]][0]), locations[0]

    def get_wavelength(self, daq_index):
        if daq_index is not None:
            return self.wavelengths[daq_index]
        
    def get_gmd(self, daq_index):
        if daq_index is not None:
            if self.gmds is not None:
                return self.gmds[daq_index]
