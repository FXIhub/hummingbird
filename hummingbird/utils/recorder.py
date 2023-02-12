# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import absolute_import  # Compatibility with python 2 and 3
from __future__ import print_function

import datetime
import logging
import os
import time

import h5py
import numpy as np


class Recorder:
    def __init__(self, outpath, events, rank, maxEvents=1000):
        self.outpath = outpath
        self.maxlen = maxEvents
        self.events = events
        self.rank = rank
        self.index = 0
        self.current_run = -1
        #self.create_file()
        self.perm_vars = ['LCLS/'+name for name in ['timestamp', 'fiducial', 'run']]
        self.perm_types = [np.uint64, np.int32, np.int32]

    def _timestamp(self):
        dt64 = np.datetime64(datetime.datetime.utcnow())
        timestamp = str(dt64)[:-5]
        return timestamp

    def setup_file_if_needed(self, evt):
        # Test whether it is a new run, non-run data counts as run 0
        run = evt["eventID"]['Timestamp'].run
        if run > 1000:
            run = 0
        #if run == self.current_run:
        #    return True
        self.current_run = run
        
        # Filename: hits_<run>_<rank>
        if run:
            self.filename = self.outpath + '/hits_%.3d_%.2d.h5' % (run, self.rank)
        else:
            return False
            #self.filename = self.outpath + '/hits_%.3d_%.2d.h5' % (run, self.rank)
        if os.path.isfile(self.filename):
            try:
                file = h5py.File(self.filename, 'a')
                self.index = len(file['LCLS/fiducial'][:])
            except IOError:
                print("Could not open file: ", self.filename)
                return False
        else:
            try:
                file = h5py.File(self.filename, 'a')
            except IOError:
                print("Could not open file: ", self.filename)
                return False
            print("Opened new file: ", self.filename)

            file.create_group('LCLS')
            for key,type in zip(self.perm_vars,self.perm_types):
                axes = 'experiment_identifier:value'
                file.create_dataset(key, (1,), maxshape=(None,), dtype=type)
                file[key].attrs.modify('axes', [axes])
            
            for key,item in self.events.items():
                group = os.path.dirname(key)
                if group == '':
                    logging.error('Record entries need to be in a group')
                    return False
                else:
                    self.make_group(file, group)
                
                item_shape = evt[item[0]][item[1]].data.shape
                item_type = evt[item[0]][item[1]].data.dtype
                ndims = len(item_shape)
                
                axes = "experiment_identifier"
                if ndims == 0: axes = 'experiment_identifier:value'
                elif ndims == 1: axes = axes + ":x"
                elif ndims == 2: axes = axes + ":y:x"
                elif ndims == 3: axes = axes + ":z:y:x"
                
                file.create_dataset(key, (0,) + item_shape, maxshape=(None,) + item_shape, dtype=item_type, chunks=(1,)+item_shape)
                file[key].attrs.modify('axes', [axes])
            file.close()
        return True

    def append(self, evt):
        if self.setup_file_if_needed(evt):
            with h5py.File(self.filename, 'a') as file:
                file['LCLS/timestamp'].resize(self.index+1, axis=0)
                file['LCLS/timestamp'][self.index] = evt["eventID"]["Timestamp"].timestamp2
                file['LCLS/fiducial'].resize(self.index+1, axis=0)
                file['LCLS/fiducial'][self.index] = evt["eventID"]["Timestamp"].fiducials
                file['LCLS/run'].resize(self.index+1, axis=0)
                file['LCLS/run'][self.index] = evt["eventID"]["Timestamp"].run
                for key, item in self.events.items():
                    file[key].resize(self.index+1, axis=0)
                    file[key][self.index] = evt[item[0]][item[1]].data
            self.index += 1

    def make_group(self, file, group_name):
        if group_name not in file:
            file.create_group(group_name)
