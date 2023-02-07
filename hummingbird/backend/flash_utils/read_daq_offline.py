import os
import time

import h5py
import numpy

import camp.pah.h5filedataaccess
from camp.pah.beamtimedaqaccess import BeamtimeDaqAccess


class DAQReader(object):
    def __init__(self, experiment_dir):
        self._dir = experiment_dir
        self._daq = BeamtimeDaqAccess.create(experiment_dir)

    def get_tof(self, event_id):
        try:
            #print(event_id)
            tof = self._daq.valuesOfInterval("/Experiment/BL1/ADQ412 GHz ADC/CH00/TD", (event_id, event_id+1))
            return tof[0, :]
        except camp.pah.h5filedataaccess.NoDaqDataException:
            return None

if __name__ == "__main__":
    reader = DAQReader("/data/beamline/current/raw/hdf/block-01/exp2/")
    start_id = 3584520
    for event_id in range(start_id, start_id+100):
        tof_trace = reader.get_tof(event_id)
        if tof_trace is not None:
            print(tof_trace)
            print(tof_trace.shape)
        else:
            print("No tof data")
