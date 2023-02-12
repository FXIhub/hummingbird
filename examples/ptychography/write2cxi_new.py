import os
import sys
import time

import h5py
import numpy as np

from hummingbird import analysis, ipc, simulation, utils

# Physical constants (from http://physics.nist.gov/)
h    = 6.626070040e-34 # [J s]
c    = np.double(2.99792458e8)    # [m/s]
hev  = np.double(4.135667662e-15) # [eV s]
ev2J = np.double(1.60217657e-19)  # [J/eV]

# Simulate a simple ptychography experiment
photon_energy_keV = 6 # keV
photon_energy_J   = np.double(photon_energy_keV * 1000.) * ev2J  # J
wavelength        = (hev*c) / np.double(photon_energy_keV * 1000.) # m
focus_diameter    = 500e-9 # m
pulse_energy      = 4e-3 # J
transmission      = 1e-8
det_pixelsize     = 110e-6 # m
det_distance      = 2.4 # m
det_sidelength    = 20 # px
det_aduphoton     = 30 # Nr. of ADUs per photon
scan_exposure     = 1 # Shots (exposures) per position
scan_x, scan_y    = (30,30) # px
scan_step         = 400e-9 # m
sample_size       = 80e-6  # m
sample_thickness  = 200e-9 # m
sample_material   = 'gold'
corner_position   = [det_sidelength/2 * det_pixelsize, det_sidelength/2 * det_pixelsize, det_distance]

sim = simulation.ptycho.Simulation()
sim.setSource(wavelength=wavelength, focus_diameter=focus_diameter,
              pulse_energy=pulse_energy, transmission=transmission)
sim.setDetector(pixelsize=det_pixelsize, nx=det_sidelength,
                distance=det_distance, adus_per_photon=det_aduphoton)
sim.setScan(nperpos=scan_exposure, scanx=scan_x, scany=scan_y,
            step=scan_step, start=(0, 0))
sim.setObject(sample='logo', size=sample_size,
              thickness=sample_thickness, material=sample_material)
sim.setIllumination(shape='gaussian')
print("Simulating a scanning experiment, this might take a few seconds...")
sim.start()

state = {
    'Facility': 'Dummy',
    'Dummy': {
        'Repetition Rate' : 100,
        'Data Sources': {
            'CCD': {
                'data': lambda: sim.get_nextframe(),
                'unit': 'ADU',     
                'type': 'photonPixelDetectors'
            },
            'position_x': {
                'data': lambda: sim.get_position_x(),
                'unit': 'm',
                'type': 'simulation'
            },
            'position_y': {
                'data': lambda: sim.get_position_y(),
                'unit': 'm',
                'type': 'simulation'
            },
            'position_z': {
                'data': lambda: 0.,
                'unit': 'm',
                'type': 'simulation'
            },
            'end':{
                'data': lambda: sim.get_end_of_scan(),
                'unit':'',
                'type': 'simulation'
            }
        }        
    }
}

if ipc.mpi.is_worker():

    # Open a CXI file
    filename = "test.cxi"
    W = utils.cxiwriter.CXIWriter(filename, chunksize=100)

    # Build tree for ptychography datasets, see http://www.cxidb.org/cxi.html
    init_dict = {}
    init_dict['entry_1'] = {}
    init_dict['entry_1']['instrument_1'] = {}
    init_dict['entry_1']['instrument_1']['detector_1'] = {}
    init_dict['entry_1']['instrument_1']['source_1'] = {}
    init_dict['entry_1']['sample_1'] = {}
    init_dict['entry_1']['sample_1']['geometry_1'] = {}
    init_dict['entry_1']['data_1'] = {}

    # Handles for detector/source/geometry
    entry_1    = init_dict['entry_1']
    detector_1 = init_dict['entry_1']['instrument_1']['detector_1']
    source_1   = init_dict['entry_1']['instrument_1']['source_1']
    geometry_1 = init_dict['entry_1']['sample_1']['geometry_1']
    data_1     = init_dict['entry_1']['data_1']

    # Add initial data to CXI file (non-stacks)
    init_dict['cxi_version'] = 140
    source_1['energy'] = photon_energy_J
    detector_1['distance'] = det_distance
    detector_1['x_pixel_size'] = det_pixelsize
    detector_1['y_pixel_size'] = det_pixelsize
    detector_1['corner_position'] = corner_position

    # Add soft links
    detector_1['translation'] = h5py.SoftLink('/entry_1/sample_1/geometry_1/translation')
    data_1['data'] = h5py.SoftLink('/entry_1/instrument_1/detector_1/data')
    data_1['translation'] = h5py.SoftLink('/entry_1/sample_1/geometry_1/translation')
    
    # These are optional data that should be provided (if known)
    # ----------------------------------------------------------
    source_1['illumination'] = sim.get_illumination()
    #detector_1['Fillumination_mask'] = ...
    #detector_1['solution'] = ...
    #detector_1['initial_image'] = ...

    # Write non-stacks to CXI file
    W.write_solo(init_dict)
    
    # This is the backbone we are going to use to extend the CXI file with data frames and translation vectors
    extend_dict= {'entry_1':{'instrument_1':{'detector_1':{}},
                         'sample_1':{'geometry_1':{}}}}


def onEvent(evt):
    
    # Processin rate [Hz]
    analysis.event.printProcessingRate()
    
    # Translation vector
    x = evt['simulation']['position_x'].data 
    y = evt['simulation']['position_y'].data
    z = evt['simulation']['position_z'].data
    translations = np.array([x,y,z])
    
    # Add data frames to CXI file
    D = extend_dict.copy()
    D["entry_1"]["instrument_1"]["detector_1"]["data"] = evt['photonPixelDetectors']['CCD'].data
    D["entry_1"]["sample_1"]["geometry_1"]["translation"] = translations
    W.write_slice(D)
    
    # Stop running at the end of the scan
    if evt['simulation']['end'].data:
        print("Reached the end of the scan")
        end_of_run()

def end_of_run():
    
    # Close CXI file
    W.close()
