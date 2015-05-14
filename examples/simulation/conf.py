import time
import analysis.event
import analysis.beamline
import analysis.background
import analysis.pixel_detector
import plotting.image
import plotting.line
import plotting.correlation
import ipc
import numpy
from backend import ureg

# Simulation using condor
# ----------------------
class Simulation:
    def __init__(self, conf):
        import condor

        # Input from config file
        I = condor.Input(conf)
        C = I.confDict

        # Convert between intensity in focus (ph/um2) and pulse energy (J)
        h = 6.62606957e-34 #Js
        c = 299792458 #m/s
        hc = h*c  #Jm
        focus_area = (0.5*I.source.profile.focus_diameter)**2 * numpy.pi # m2
        intensity2pulse = lambda i: i * focus_area * 1e12 * hc / I.source.photon.get_wavelength() # J
        pulse2intensity = lambda p: p * I.source.photon.get_wavelength() / (focus_area * 1e12 * hc) 

        # Change input
        pulseEnergy_mean   = intensity2pulse(0.5e13)
        pulseEnergy_spread = intensity2pulse(0.9e12)
        print pulseEnergy_mean, pulseEnergy_spread
        C["source"]["pulse_energy"] = pulseEnergy_mean
        C["source"]["pulse_energy_spread"] = pulseEnergy_spread
        I = condor.Input(C)

        # Output
        O = condor.Output(I)
        self.data = O.intensity_pattern
        self.mask = O.mask
        self.position = O.outdict["sample"]["position"]
        self.intensity = pulse2intensity(O.outdict["source"]["pulse_energy"])
        self.particle_size = O.outdict["sample"]["diameter"]
        
        self.index = 0

    def next_event(self):
        self.index = (self.index + 1) % self.data.shape[0]

    def get_pattern(self):
        return self.data[self.index] * self.mask[self.index]

    def get_intensity(self):
        return self.intensity[self.index]

    def get_particle_size(self):
        return self.particle_size[self.index,0] * 1e9

    def get_position_x(self):
        return self.position[self.index][0][0]
    
sim = Simulation("examples/simulation/condor.conf")
        
state = {
    'Facility': 'Dummy',

    'Dummy': {
        'Repetition Rate' : 10,
        'Data Sources': {
            'CCD': {
                'data': sim.get_pattern,
                'unit': ureg.ph,     
                'type': 'photonPixelDetectors'
            },
            'inj_x': {
                'data': sim.get_position_x,
                'unit': ureg.m,
                'type': 'parameters'
            },
            'intensity': {
                'data': sim.get_intensity,
                'unit': None,
                'type': 'parameters'
            },
            'particle_size': {
                'data': sim.get_particle_size,
                'unit': ureg.nm,
                'type': 'parameters'
            }
        }        
    }
}

def onEvent(evt):
    sim.next_event()
    ipc.broadcast.init_data('CCD', xmin=10,ymin=10)
    for k,v in evt['photonPixelDetectors'].iteritems():
        plotting.image.plotImage(v)
    plotting.line.plotHistory(evt["parameters"]["inj_x"])
    plotting.line.plotHistory(evt["parameters"]["intensity"])
    plotting.line.plotHistory(evt["parameters"]["particle_size"])
    #plotting.correlation.plotHeatmap(evt["parameters"]["particle_size"], evt["parameters"]["intensity"], xmin=30e-9, xmax=90e-9, xbins=60)
    analysis.event.printProcessingRate()
    analysis.event.printKeys(evt)
