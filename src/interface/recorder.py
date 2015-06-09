import time
import h5py
import sys

class H5Recorder:
    """Recording event variables to an HDF5 file.

    .. note::
        When reading from the recorder file, it might be necesssary to sort them using the timestamp before comparing different datasets.
    """
    def __init__(self, outpath, maxFileSizeGB=1):
        self.outpath   = outpath
        self.maxGBytes = maxFileSizeGB
        self._fileBytes = 0
        self._indices  = {}
        
    def _timestamp(self):
        t = time.localtime()
        timestamp = str(t.tm_year) + '%02d' %t.tm_mon + '%02d' %t.tm_mday + \
                    '_' + '%02d' %t.tm_hour + '%02d' %t.tm_min
        return timestamp
        
    def openfile(self):
        """Open new file using a unique filename."""
        filename = self.outpath + '/history_' + self._timestamp() + '.h5'
        self._file = h5py.File(filename, 'a')
        print "Opened new file: ", filename

    def closefile(self):
        """Close existing file."""
        print "Closed file: ", self._file.filename
        time.sleep(1)
        self._file.close()

    def append(self, title, data, data_x):
        """Append a tuple of time and event variable to dataset with the name of the variable."""
        key = title.split('(')[-1].split(')')[0].split('/')[-1]
        if key not in self._file.keys():
            self._file.create_dataset(key, (2, 1000), maxshape=(2, None), dtype=type(data_x))
            self._indices[key] = 0
        self._file[key][:,self._indices[key]] = [data_x, data]
        self._indices[key] += 1
        if self._indices[key] == self._file[key].shape[1]:
            self._file[key].resize((2, self._file[key].shape[1]+1000))
        self._fileBytes += (sys.getsizeof(data_x) + sys.getsizeof(data))
        if int(self._fileBytes // (1e9*self.maxGBytes)):
            self.closefile()
            self._fileBytes = 0
            self.openfile()