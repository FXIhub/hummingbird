import analysis.event
import analysis.beamline
import analysis.pixel_detector
import analysis.hitfinding
import utils.cxiwriter
import simulation.ptycho
import ipc.mpi

import numpy as np
import os,sys
import time
import h5py

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
print "Simulating a scanning experiment, this might take a few seconds..."
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


# This necessary for MPI (should be moved out of this file)
mpi = ipc.mpi.comm.size > 1
comm = ipc.mpi.slaves_comm if mpi else None
is_slave = ipc.mpi.is_master() == False
if is_slave and mpi:
    size = comm.size
    rank = comm.rank
else:
    size = 1
    rank = 0

# Open a CXI file
filename = "test.cxi"
if is_slave:
    W = utils.cxiwriter.CXIWriter(filename, chunksize=100, comm=comm)

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
    W.write(D)

    # Stop running at the end of the scan
    if evt['simulation']['end'].data:
        print "Reached the end of the scan"
        end_of_run()

def end_of_run():
    
    # Close CXI file
    W.close()

    if ipc.mpi.is_main_worker():

        # Reopen CXI file to append with more information nessesary
        # for ptychography datasets, see http://www.cxidb.org/cxi.html
        f = h5py.File(filename, "r+")
        
        # Already existing fields
        entry_1 = f['entry_1']
        instrument_1 = f['entry_1']['instrument_1']
        detector_1   = f['entry_1']['instrument_1']['detector_1']
        sample_1     = f['entry_1']['sample_1']
        geometry_1   = f['entry_1']['sample_1']['geometry_1']

        # Add new data fields
        f.create_dataset("cxi_version",data=140)
        source_1 = instrument_1.create_group("source_1")
        source_1.create_dataset("energy", data=photon_energy_J) # in J
        detector_1.create_dataset("distance", data=det_distance) 
        detector_1.create_dataset("x_pixel_size", data=det_pixelsize)
        detector_1.create_dataset("y_pixel_size", data=det_pixelsize)
        detector_1["translation"] = h5py.SoftLink('/entry_1/sample_1/geometry_1/translation')
        detector_1.create_dataset("corner_position", data=corner_position) 
        data_1 = entry_1.create_group("data_1")
        data_1["data"] = h5py.SoftLink('/entry_1/instrument_1/detector_1/data')
        data_1["translation"] = h5py.SoftLink('/entry_1/sample_1/geometry_1/translation')

        # These are optional data that should be provided (if known)
        # ----------------------------------------------------------
        source_1.create_dataset("illumination", data=sim.get_illumination())
        #detector_1.create_dataset("Fillumination_mask", data=illumination_intensities_mask)
        #detector_1.create_dataset("solution", data=sim.obj)
        #detector_1.create_dataset("initial_image",data=initial_image)
        
        # Close CXI file and exit
        f.close()
