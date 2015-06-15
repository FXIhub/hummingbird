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
        self.index = None
        self.create_file()

    def _timestamp(self):
        dt64 = np.datetime64(datetime.datetime.utcnow())
        timestamp = str(dt64)[:-5]
        return timestamp

    def create_file(self):
        self.filename = self.outpath + '/hits_' + self._timestamp() + 'rk%02d.h5' %self.rank
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
        self.index = 0
        return True

    def append(self, evt):
        if self.index is None:
            logging.warning("Cannot record events.")
            return
        if self.index == self.maxlen:
            self.create_file()
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


    
            
