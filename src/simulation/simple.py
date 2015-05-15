import condor
import numpy

class Simulation:
    def __init__(self, conf):
        self.input = condor.Input(conf)
        self.p = condor.propagator.Propagator(self.input.source, self.input.sample, self.input.detector)
        self.nx = self.input.confDict["detector"]["nx"]
        self.ny = self.input.confDict["detector"]["ny"]
        self.sigma = self.input.confDict["detector"]["noise_spread"]
        self.reprate = 120.
        self.hitrate = 0.1
        self.counter = 0

    def hit(self):
        self.output = self.p.propagate()

    def miss(self):
        self.output = self.p.propagate()
        self.output["intensity_pattern"] = numpy.random.normal(0, self.sigma, (self.ny, self.nx)).reshape((1,self.ny,self.nx))
        
    def next_event(self):
        if not (self.counter % (self.reprate*self.hitrate)): self.hit()
        else: self.miss()
        self.counter = (self.counter+1) % self.reprate

    def get_pattern(self):
        return self.output["intensity_pattern"][0]

    def get_pulse_energy(self):
        return self.output["source"]["pulse_energy"][0]

    def get_particle_size_nm(self):
        return self.output["sample"]["diameter"][0,0] * 1e9

    def get_position_x(self):
        return self.output["sample"]["position"][0][0][0]

    def get_position_y(self):
        return self.output["sample"]["position"][0][0][1]

    def get_position_z(self):
        return self.output["sample"]["position"][0][0][2]

    
