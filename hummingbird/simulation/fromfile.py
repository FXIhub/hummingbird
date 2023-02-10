# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
import h5py
import numpy as np

from hummingbird import ipc, utils


class Simulation(utils.reader.H5Reader):
    def __init__(self, filename, datakey, pulsekey, injkey):
        utils.reader.H5Reader.__init__(self, filename)
        self.data   = self._fileno[datakey]
        self.pulse  = self._fileno[pulsekey]
        self.injpos = self._fileno[injkey]
        self.len    = self.data.shape[0]
        self.ny     = self.data.shape[1]
        self.nx     = self.data.shape[2]
        self.index  = 0

    def next_event(self):
        self.index = (self.index % self.len) + 1

    def get_pattern(self):
        return self.data[self.index]

    def get_pulse_energy(self):
        return self.pulse[self.index]

    def get_injector_pos_x(self):
        return self.injpos[self.index,0].astype(np.float)

    def get_injector_pos_y(self):
        return self.injpos[self.index,1].astype(np.float)

    def get_injector_pos_z(self):
        return self.injpos[self.index,2].astype(np.float)
