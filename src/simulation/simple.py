import condor
import numpy

class Simulation:
    def __init__(self, conf):
        self.input = condor.Input(conf)
        
    def next_event(self):
        p = condor.propagator.Propagator(self.input.source, self.input.sample, self.input.detector)
        self.output = p.propagate()

    def get_pattern(self):
        return self.output["intensity_pattern"][0]

    def get_intensity(self):
        return self.output["source"]["pulse_energy"][0]

    def get_particle_size(self):
        return self.output["sample"]["diameter"][0,0] * 1e9

    def get_position_x(self):
        return self.output["sample"]["position"][0][0][0]
