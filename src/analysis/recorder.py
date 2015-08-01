import os
import time, datetime
import h5py
import logging
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
                self.index = len(file['fiducial'][:])
            except IOError:
                print "Could not open file: ", self.filename
                return False
        else:
            try:
                file = h5py.File(self.filename, 'a')
            except IOError:
                print "Could not open file: ", self.filename
                return False
            print "Opened new file: ", self.filename
            for key in self.events:
                file.create_dataset(key, (0,), maxshape=(None,), dtype=float)
            file.create_dataset('timestamp', (0,), maxshape=(None,), dtype=np.uint64)
            file.create_dataset('fiducial',  (0,), maxshape=(None,), dtype=np.int64)
            file.create_dataset('run',  (0,), maxshape=(None,), dtype=np.int64)
            file.close()
        return True

    def append(self, evt):
        if self.setup_file_if_needed(evt):
            with h5py.File(self.filename, 'a') as file:
                file['timestamp'].resize(self.index+1, axis=0)
                file['timestamp'][self.index] = evt["eventID"]["Timestamp"].timestamp2
                file['fiducial'].resize(self.index+1, axis=0)
                file['fiducial'][self.index] = evt["eventID"]["Timestamp"].fiducials
                file['run'].resize(self.index+1, axis=0)
                file['run'][self.index] = evt["eventID"]["Timestamp"].run
                for key, item in self.events.iteritems():
                    file[key].resize(self.index+1, axis=0)
                    file[key][self.index] = evt[item[0]][item[1]].data
            self.index += 1


    
            
