import os, sys

# Make sure we are relative to the root path
__thisdir__ = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, __thisdir__ + "/../src")

# Import Hummingbird Dummy translator
from backend.dummy import DummyTranslator

# Import analysis modules
import analysis.beamline
import analysis.hitfinding

# Setting the environment for testing the analysis modules
state = {}
def setup_module(module):
        
    # Creating a dummy state for testing
    state['Facility'] = 'Dummy'
    state['Dummy'] = {
        'Data Sources': {
            'photonEnergy1': {
                'data': lambda: 4.,
                'unit': 'eV',     
                'type': 'photonEnergies'
            },
            'photonEnergy2': {
                'data': lambda: 5.,
                'unit': 'eV',     
                'type': 'photonEnergies'
            },
            'pulseEnergy1': {
                'data': lambda: 2.,
                'unit': 'mJ',     
                'type': 'pulseEnergies'
            },
            'pulseEnergy2': {
                'data': lambda: 3.,
                'unit': 'mJ',     
                'type': 'pulseEnergies'
            },
        }
    }

        
# Testing the beamline module
# ---------------------------

# Testing averaging of pulse energies
def test_beamline_average_pulse_energy():
    evt = DummyTranslator(state).next_event()
    analysis.beamline.averagePulseEnergy(evt, evt['pulseEnergies'])
    assert (evt['analysis']['averagePulseEnergy'].data == 2.5)

# Testing averaging of photon energies
def test_beamline_average_photon_energy():
    evt = DummyTranslator(state).next_event()
    analysis.beamline.averagePhotonEnergy(evt, evt['photonEnergies'])
    assert (evt['analysis']['averagePhotonEnergy'].data == 4.5)


# Testing the hitfidning module
# -----------------------------

# Testing the counting of hits
def test_hitfinding_count_hits():
    evt = DummyTranslator(state).next_event()
    for i in range(10):
        analysis.hitfinding.countHits(evt, True, outkey='nrHits1')
    assert (evt['analysis']['nrHits1'].data == 10)
    for i in range(10):
        analysis.hitfinding.countHits(evt, False, outkey='nrHits2')
    assert (evt['analysis']['nrHits2'].data == 0)
    
# Remove traces from testing the analysis modules
def teardown_module():
    sys.path.pop(0)
    
