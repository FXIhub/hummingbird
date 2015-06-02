import h5py
import numpy as np
import utils.reader

class Simulation(utils.reader.H5Reader):
    def __init__(self, filename, datakey, pulsekey):
        print filename
        utils.reader.H5Reader.__init__(self, filename)
        self.data  = self._fileno[datakey]
        self.pulse = self._fileno[pulsekey]
        self.len   = self.data.shape[0]
        self.ny    = self.data.shape[1]
        self.nx    = self.data.shape[2]
        self.index = 0

    def next_event(self):
        print self.index
        self.index = (self.index % self.len) + 1

    def get_pattern(self):
        print self.data[self.index].shape
        return self.data[self.index]

    def get_pulse_energy(self):
        print self.pulse[self.index]
        return self.pulse[self.index]

