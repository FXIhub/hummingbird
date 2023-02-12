# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
import h5py
import numpy as np


class H5Reader:
    def __init__(self, filename, key=None):
        self._fileno = h5py.File(filename, 'r')
        if key is not None:
            self.dataset = self.load_dataset(key)
            self._fileno.close()
            
    def load_dataset(self, key):
        try:
            d = self._fileno[key][:]
        except ValueError:
            d = self._fileno[key][...]
        return d
        
class MaskReader(H5Reader):
    def __init__(self, filename, key='data/data'):
        H5Reader.__init__(self, filename, key)
        self.integer_mask = self.dataset.astype(np.int)
        self.boolean_mask = self.dataset.astype(np.bool)

class GeometryReader(H5Reader):
    def __init__(self, filename, pixel_size=1.):
        H5Reader.__init__(self, filename)
        self.x = self._fileno['x'][:] / pixel_size
        self.y = self._fileno['y'][:] / pixel_size
        self.x = np.round(self.x).astype(np.int)
        self.y = np.round(self.y).astype(np.int)
        self._fileno.close()
