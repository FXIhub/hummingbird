import time
import analysis.event
import analysis.beamline
import analysis.background
import analysis.pixel_detector
import plotting.image
import plotting.line
import ipc
import numpy
from backend import ureg

# Simulation using condor
# ----------------------
class Simulation:
    def __init__(self, conf):
        import condor
        I = condor.Input(conf)
        C = I.confDict
        # ... here we could change the configuration
        O = condor.Output(I)
        self.data = O.intensity_pattern
        self.mask = O.mask
        self.position = O.outdict["sample"]["position"]
        self.index = 0

    def next_event(self):
        self.index = (self.index + 1) % self.data.shape[0]

    def get_pattern(self):
        return self.data[self.index] * self.mask[self.index]

    def get_position_x(self):
        return self.position[self.index][0][0]
    
condor_config = "/Users/benedikt/phd-project/experiments/SPI_June2015/BestPhotonEnergy/sizing/rdv_7keV.conf"
sim = Simulation(condor_config)
        
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
                'type': 'parameters',
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
    analysis.event.printProcessingRate()
    analysis.event.printKeys(evt)
