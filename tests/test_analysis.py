import os, sys
import numpy as np

# Make sure we are relative to the root path
__thisdir__ = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, __thisdir__)

# Import Hummingbird Dummy translator
from hummingbird.backend.dummy import DummyTranslator

# Import analysis modules
from hummingbird import analysis


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
            'CCDlow': {
            'data': lambda: np.random.randint(0, 20, size=(128, 128)).astype(np.float32),
            'unit': 'ADU',     
            'type': 'photonPixelDetectors'
            },
            'CCDstrong': {
            'data': lambda: np.ones((128, 128))*21.,
            'unit': 'ADU',     
            'type': 'photonPixelDetectors'
            },
            'TOF':{'data': lambda: np.ones(10)*5.,
                   'unit': 'au',
                   'type': 'ionTOFs'
            }
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

# Testing hitrate
def test_hitfinding_hitrate():
    evt = DummyTranslator(state).next_event()
    for i in range(10):
        analysis.hitfinding.hitrate(evt, True, history=10, outkey='hitrate1')
        analysis.hitfinding.hitrate(evt, False, history=10, outkey='hitrate2')
    assert (evt['analysis']['hitrate1'].data == 100.)
    assert (evt['analysis']['hitrate2'].data == 0.)
    for i in range(5):
        analysis.hitfinding.hitrate(evt, False, history=10, outkey='hitrate1')
    assert (evt['analysis']['hitrate1'].data == 50.)

# Testing count lit pixels
def test_hitfinding_countLitPixels():
    evt = DummyTranslator(state).next_event()
    analysis.hitfinding.countLitPixels(evt, evt['photonPixelDetectors']['CCDlow'], aduThreshold=20, hitscoreThreshold=200, hitscoreDark=0)
    assert (evt['analysis']['litpixel: isHit'].data == 0)
    assert (evt['analysis']['litpixel: isMiss'].data == 0)
    assert (evt['analysis']['litpixel: hitscore'].data == 0)
    analysis.hitfinding.countLitPixels(evt, evt['photonPixelDetectors']['CCDstrong'], aduThreshold=20, hitscoreThreshold=200, hitscoreDark=0)
    assert (evt['analysis']['litpixel: isHit'].data == 1)
    assert (evt['analysis']['litpixel: isMiss'].data == 0)
    assert (evt['analysis']['litpixel: hitscore'].data == 128*128)

# Testing Tof hitfinder
def test_countTof():
    evt = DummyTranslator(state).next_event()
    analysis.hitfinding.countTof(evt, evt['ionTOFs']['TOF'], outkey='tof1: ')
    assert (evt['analysis']['tof1: isHit'].data.sum() == 0)
    assert (evt['analysis']['tof1: hitscore'].data.sum() == 9)

# Testing hitscore count
def test_countHitscore():
    evt = DummyTranslator(state).next_event()
    analysis.hitfinding.countHitscore(evt, 10)
    assert evt['analysis']['predef: isHit'].data == False
    assert evt['analysis']['predef: hitscore'].data == 10
    analysis.hitfinding.countHitscore(evt, 300)
    assert evt['analysis']['predef: isHit'].data == True
    assert evt['analysis']['predef: hitscore'].data == 300

# Testing photon count vs energy
#def test_countPhotonsvsEnergy():
#    evt = DummyTranslator(state).next_event()
#    analysis.countPhotonsAgainstEnergyFunction(evt, )

# Remove traces from testing the analysis modules
def teardown_module():
    sys.path.pop(0)
    
