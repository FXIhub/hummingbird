import condor
import numpy

class Simulation:
    def __init__(self, conf):
        self.input = condor.Input(conf)
        self.p = condor.propagator.Propagator(self.input.source, self.input.sample, self.input.detector)
        self.nx = self.input.confDict["detector"]["nx"]
        self.ny = self.input.confDict["detector"]["ny"]
        self.cx_mean = self.input.detector.get_cx_mean_value()
        self.cy_mean = self.input.detector.get_cy_mean_value()
        self.sigma = self.input.confDict["detector"]["noise_spread"]
        self.hitrate = 0.1

    def hit(self):
        self.output = self.p.propagate()

    def miss(self):
        self.output = self.p.propagate()
        self.output["intensity_pattern"] = numpy.random.normal(0, self.sigma, (self.ny, self.nx)).reshape((1,self.ny,self.nx))
        
    def next_event(self):
        if numpy.random.rand() < self.hitrate: self.hit()
        else: self.miss()

    def get_pattern(self):
        return self.output["intensity_pattern"][0]

    def get_pulse_energy(self):
        return self.output["source"]["pulse_energy"][0]

    def get_intensity_mJ_um2(self):
        I = self.output["sample"]["intensity"][0,0]
        E = self.output["source"]["photon_energy"][0]
        return (I*E/1E-3*1E-12)
    
    def get_particle_diameter_nm(self):
        return self.output["sample"]["diameter"][0,0] * 1e9

    def get_offCenterX(self):
        return self.output["detector"]["cx"]-self.cx_mean

    def get_offCenterY(self):
        return self.output["detector"]["cy"]-self.cy_mean

    def get_flattening(self):
        return self.output["sample"]["flattening"][0,0]

