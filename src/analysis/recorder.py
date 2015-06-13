import h5py
import numpy as np

class Recorder:
    def __init__(outpath, events, rank, maxEvents=1000):
        self.outpath = outpath
        self.maxlen = maxEvents
        self.events = events
        self.rank = rank
        self.index = 0

    def _timestamp(self):
        t = time.localtime()
        timestamp = str(t.tm_year) + '%02d' %t.tm_mon + '%02d' %t.tm_mday + \
                    '_' + '%02d' %t.tm_hour + '%02d' %t.tm_min
        return timestamp

    def create_file(self):
        self.filename = self.outpath + '/hits_' + self._timestamp() + 'rk' + self.rank + '.h5'
        try:
            file = h5py.File(filename, 'a')
        except IOError:
            print "Could not open file: ", filename
            return False
        print "Opened new file: ", filename
        for key in self.events:
            file.create_dataset(key, (self.maxlen,), dtype=float)
        file.create_dataset('timestamp', (self.maxlen,), dtype=np.uint64)
        file.close()
        return True

    def append(self, evt):
        with h5py.File(filename, 'a') as file:
            file['timestamp'][self.index] = evt["eventID"]["Timestamp"].lcls_time
            for key, item in self.events.iteritems:
                self._file[key][self.index] = evt[item[0]][item[1]].data
        self.index += 1


    
            
