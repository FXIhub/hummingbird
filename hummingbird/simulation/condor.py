# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
import numpy

import condor

from hummingbird import utils


class Simulation:
    def __init__(self, conf):
        success, module = utils.io.load_condor()
        if not success:
            print("Could not run simulation")
            return
        self.e = module.experiment.experiment_from_configfile(conf)
        self._nx = self.e.detector.get_mask().shape[1]
        self._ny = self.e.detector.get_mask().shape[0]
        self._cx_mean = self.e.detector.get_cx_mean_value()
        self._cy_mean = self.e.detector.get_cy_mean_value()
        self.hitrate = 0.1
        self._is_hit = None
        self._output = None

    def hit(self):
        self._output = self.e.propagate()
        self._is_hit = True

    def miss(self):
        self._is_hit = False

    def get_is_hit(self):
        return self._is_hit
        
    def next_event(self):
        if numpy.random.rand() < self.hitrate: self.hit()
        else: self.miss()

    def get_pattern(self):
        if self._is_hit:
            return self._output["entry_1"]["data_1"]["data"]
        else:
            return self.e.detector.detect_photons(numpy.zeros(shape=(self._ny, self._nx)))[0]

    def get_mask(self):
        if self._is_hit:
            return self._output["entry_1"]["data_1"]["mask"]
        else:
            # This is not quite right, it should be rather coupled with get_pattern call
            return self.e.detector.detect_photons(numpy.zeros(shape=(self._ny, self._nx)))[1]

    def get_pulse_energy(self):
        if self._is_hit:
            return self._output["source"]["pulse_energy"]
        else:
            return self.e.source.get_next()["pulse_energy"]

    def get_intensity_mJ_um2(self):
        if self._is_hit:
            I = self._output["particles"]["particle_00"]["intensity"]
            E = self._output["source"]["photon_energy"]
            return (I*E/1E-3*1E-12)
        else:
            return 0.

    def get_intensity(self):
        if self._is_hit:
            I = self._output["particles"]["particle_00"]["intensity"]
            E = self._output["source"]["photon_energy"]
            return I*E
        else:
            return 0.
        
    def get_particle_diameter_nm(self):
        if self._is_hit:
            return self._output["particles"]["particle_00"]["diameter"] * 1e9
        else:
            return None

    def get_particle_diameter(self):
        if self._is_hit:
            return self._output["particles"]["particle_00"]["diameter"]
        else:
            return None

    def get_particle_number(self):
        if self._is_hit:
            return len(self._output["particles"].keys())
        else:
            return 0

    def get_offCenterX(self):
        if self._is_hit:
            return self._output["detector"]["cx"]-self._cx_mean
        else:
            return None

    def get_offCenterY(self):
        if self._is_hit:
            return self._output["detector"]["cy"]-self._cy_mean
        else:
            return None

    def get_cx(self):
        if self._is_hit:
            return self._output["detector"]["cx"]
        else:
            return None
        
    def get_cy(self):
        if self._is_hit:
            return self._output["detector"]["cy"]
        else:
            return None

    def get_injector_x(self):
        if self._is_hit:
            return self._output["particles"]["particle_00"]["position"][0]*(1e9)
        else:
            return None

    def get_injector_y(self):
        if self._is_hit:
            return self._output["particles"]["particle_00"]["position"][1]*(1e9)
        else:
            return None

    def get_injector_z(self):
        if self._is_hit:
            return self._output["particles"]["particle_00"]["position"][2]*(1e9)
        else:
            return None
